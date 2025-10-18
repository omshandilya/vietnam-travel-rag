from neo4j import GraphDatabase
import config

def check_database():
    driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Count nodes by type
        print("=== NODE COUNTS BY TYPE ===")
        result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count ORDER BY count DESC")
        for record in result:
            print(f"{record['labels']}: {record['count']}")
        
        print("\n=== TOTAL NODES ===")
        total = session.run("MATCH (n) RETURN count(n) as total").single()["total"]
        print(f"Total nodes: {total}")
        
        print("\n=== RELATIONSHIP COUNTS ===")
        rel_result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC")
        for record in rel_result:
            print(f"{record['rel_type']}: {record['count']}")
        
        print("\n=== SAMPLE CITIES ===")
        cities = session.run("MATCH (c:City) RETURN c.name, c.id LIMIT 5")
        for record in cities:
            print(f"City: {record['c.name']} (ID: {record['c.id']})")
        
        print("\n=== HANOI CONNECTIONS ===")
        hanoi_connections = session.run("""
            MATCH (hanoi:City {name: 'Hanoi'})-[r]-(connected)
            RETURN type(r) as relation, connected.name as name, labels(connected) as type
            LIMIT 10
        """)
        for record in hanoi_connections:
            print(f"Hanoi {record['relation']} {record['name']} ({record['type']})")
    
    driver.close()

if __name__ == "__main__":
    check_database()