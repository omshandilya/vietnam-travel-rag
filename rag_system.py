import json
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from neo4j import GraphDatabase
import config

class VietnamTravelRAG:
    def __init__(self):
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
        self.index = self.pc.Index(config.PINECONE_INDEX_NAME)
        
        # Initialize Neo4j
        self.neo4j_driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
    
    def close(self):
        self.neo4j_driver.close()
    
    def search_similar(self, query, top_k=5):
        """Search for similar items using Pinecone"""
        # Generate embedding for query
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        # Search in Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        return results['matches']
    
    def get_related_items(self, item_id):
        """Get related items using Neo4j relationships"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (source {id: $item_id})-[r]->(target)
                RETURN target.id as id, target.name as name, 
                       target.description as description, type(r) as relation
                LIMIT 10
            """, item_id=item_id)
            
            return [dict(record) for record in result]
    
    def search(self, query):
        """Main search function combining vector and graph search"""
        print(f"Searching for: {query}")
        print("=" * 50)
        
        # 1. Vector search with Pinecone
        similar_items = self.search_similar(query, top_k=3)
        
        print("SIMILAR PLACES:")
        for i, item in enumerate(similar_items, 1):
            metadata = item['metadata']
            score = item['score']
            print(f"{i}. {metadata['name']} ({metadata['type']})")
            print(f"   Location: {metadata.get('city', 'N/A')}")
            print(f"   Similarity: {score:.3f}")
            print()
        
        # 2. Graph search for relationships
        if similar_items:
            top_item_id = similar_items[0]['metadata']['id']
            related_items = self.get_related_items(top_item_id)
            
            if related_items:
                print("RELATED PLACES:")
                for i, item in enumerate(related_items, 1):
                    print(f"{i}. {item['name']} ({item['relation']})")
                    if item['description']:
                        print(f"   {item['description'][:100]}...")
                    print()        
        return {
            'similar_items': similar_items,
            'related_items': related_items if similar_items else []
        }

def main():
    rag = VietnamTravelRAG()
    
    try:
        queries = [
            "beautiful beaches and water activities",
            "cultural heritage and temples",
            "mountain trekking and nature"
        ]
        
        for query in queries:
            results = rag.search(query)
            print("\n" + "="*60 + "\n")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        rag.close()

if __name__ == "__main__":
    main()