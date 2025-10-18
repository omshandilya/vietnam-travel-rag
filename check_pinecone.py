from pinecone import Pinecone
import config

def check_pinecone_data():
    """Check Pinecone index statistics and sample data"""
    
    # Initialize Pinecone
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    index = pc.Index(config.PINECONE_INDEX_NAME)
    
    print("=== PINECONE INDEX STATUS ===")
    
    # Get index stats
    try:
        stats = index.describe_index_stats()
        print(f"Index Name: {config.PINECONE_INDEX_NAME}")
        print(f"Total Vectors: {stats.total_vector_count}")
        print(f"Index Dimension: {stats.dimension}")
        
        if hasattr(stats, 'namespaces'):
            for namespace, info in stats.namespaces.items():
                print(f"Namespace '{namespace}': {info.vector_count} vectors")
        
    except Exception as e:
        print(f"Error getting index stats: {e}")
        return
    
    print("\n=== SAMPLE QUERY TEST ===")
    
    # Test query to see if data exists
    try:
        # Create a dummy vector for testing
        test_vector = [0.1] * 384  # 384 dimensions for sentence-transformers
        
        results = index.query(
            vector=test_vector,
            top_k=10,
            include_metadata=True
        )
        
        print(f"Query returned {len(results.matches)} results")
        
        if results.matches:
            print("\nSample results:")
            for i, match in enumerate(results.matches[:5], 1):
                metadata = match.metadata
                print(f"{i}. ID: {match.id}")
                print(f"   Name: {metadata.get('name', 'N/A')}")
                print(f"   Type: {metadata.get('type', 'N/A')}")
                print(f"   City: {metadata.get('city', 'N/A')}")
                print(f"   Score: {match.score:.4f}")
                print()
        else:
            print("No results found - index might be empty!")
            
    except Exception as e:
        print(f"Error querying index: {e}")

if __name__ == "__main__":
    check_pinecone_data()