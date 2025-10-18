import json
from neo4j import GraphDatabase
from tqdm import tqdm
import config

class Neo4jUploader:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear existing data"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared")
    
    def create_constraints(self):
        """Create unique constraints"""
        with self.driver.session() as session:
            # Generic Entity constraint + specific type constraints
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:City) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Attraction) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (h:Hotel) REQUIRE h.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (act:Activity) REQUIRE act.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                session.execute_write(lambda tx: tx.run(constraint))
            print("Constraints created")
    
    def upload_nodes(self, data):
        """Upload all nodes to Neo4j using MERGE for idempotent operations"""
        with self.driver.session() as session:
            for item in tqdm(data, desc="Creating nodes"):
                session.execute_write(self._upsert_node, item)
        print(f"Uploaded {len(data)} nodes")
    
    def _upsert_node(self, tx, item):
        """Upsert a single node with dynamic properties"""
        node_type = item.get('type', 'Unknown')
        # Exclude connections from properties
        props = {k: v for k, v in item.items() if k not in ('connections',)}
        
        # Use MERGE for idempotent operations + add Entity label
        tx.run(f"""
            MERGE (n:{node_type}:Entity {{id: $id}})
            SET n += $props
        """, id=item['id'], props=props)
    
    def create_relationships(self, data):
        """Create relationships between nodes using MERGE"""
        with self.driver.session() as session:
            for item in tqdm(data, desc="Creating relationships"):
                connections = item.get('connections', [])
                for connection in connections:
                    session.execute_write(self._create_relationship, item['id'], connection)
        print("Relationships created")
    
    def _create_relationship(self, tx, source_id, connection):
        """Create a single relationship"""
        rel_type = connection.get('relation', 'RELATED_TO')
        target_id = connection.get('target')
        if not target_id:
            return
        
        # Use MERGE for idempotent relationship creation
        tx.run(f"""
            MATCH (a:Entity {{id: $source_id}}), (b:Entity {{id: $target_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            RETURN r
        """, source_id=source_id, target_id=target_id)

def main():
    # Load data
    with open('vietnam_travel_database.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Upload to Neo4j
    uploader = Neo4jUploader()
    
    try:
        print("Starting Neo4j upload...")
        uploader.clear_database()
        uploader.create_constraints()
        uploader.upload_nodes(data)
        uploader.create_relationships(data)
        print("Neo4j upload completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        uploader.close()

if __name__ == "__main__":
    main()