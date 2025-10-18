import json
import asyncio
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from neo4j import GraphDatabase
from openai import OpenAI
import config

class VietnamTravelChatbot:
    def __init__(self):
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Embedding cache
        self.embedding_cache = {}
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
        self.index = self.pc.Index(config.PINECONE_INDEX_NAME)
        
        # Initialize Neo4j
        self.neo4j_driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
        
        # Initialize OpenRouter LLM
        self.llm_client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )
    
    def close(self):
        self.neo4j_driver.close()
    
    def get_cached_embedding(self, query):
        """Get embedding with caching"""
        if query in self.embedding_cache:
            return self.embedding_cache[query]
        
        embedding = self.embedding_model.encode([query]).tolist()[0]
        self.embedding_cache[query] = embedding
        return embedding
    
    async def search_similar_async(self, query, top_k=5):
        """Async search for similar items using Pinecone"""
        query_embedding = self.get_cached_embedding(query)
        
        # Run Pinecone query in thread pool since it's not async
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, 
            lambda: self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
        )
        
        return results['matches']
    
    def search_similar(self, query, top_k=5):
        """Search for similar items using Pinecone (sync version)"""
        query_embedding = self.get_cached_embedding(query)
        
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        return results['matches']
    
    async def get_related_items_async(self, item_ids):
        """Async get related items using Neo4j relationships"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_related_items, item_ids)
    
    def get_related_items(self, item_ids):
        """Get related items using Neo4j relationships for multiple IDs"""
        facts = []
        with self.neo4j_driver.session() as session:
            for item_id in item_ids:
                result = session.run("""
                    MATCH (source {id: $item_id})-[r]->(target)
                    RETURN target.id as id, target.name as name, 
                           target.description as description, type(r) as relation
                    LIMIT 3
                """, item_id=item_id)
                
                for record in result:
                    facts.append({
                        "source": item_id,
                        "relation": record["relation"],
                        "target_name": record["name"],
                        "target_desc": (record["description"] or "")[:200]
                    })
        
        return facts
    
    def search_summary(self, similar_items, related_items):
        """Generate a quick summary of search results"""
        cities = set()
        types = set()
        
        for item in similar_items:
            meta = item['metadata']
            if meta.get('city'):
                cities.add(meta['city'])
            if meta.get('type'):
                types.add(meta['type'])
        
        summary = f"Found {len(similar_items)} places"
        if cities:
            summary += f" across {len(cities)} cities ({', '.join(list(cities)[:3])})"
        if types:
            summary += f" including {', '.join(types)}"
        if related_items:
            summary += f" with {len(related_items)} related connections"
        
        return summary
    
    async def get_rag_context_async(self, query):
        """Async get context from both vector and graph search in parallel"""
        # Run vector and graph searches in parallel
        similar_task = self.search_similar_async(query, top_k=5)
        
        # Start vector search
        similar_items = await similar_task
        
        # Start graph search if we have results
        if similar_items:
            top_item_ids = [item['metadata']['id'] for item in similar_items[:3]]
            related_items = await self.get_related_items_async(top_item_ids)
        else:
            related_items = []
        
        # Generate summary
        summary = self.search_summary(similar_items, related_items)
        print(f"SUMMARY: {summary}")
        
        return similar_items, related_items
    
    def get_rag_context(self, query):
        """Get context from both vector and graph search (sync version)"""
        # Vector search
        similar_items = self.search_similar(query, top_k=5)
        
        # Graph search for multiple top results
        related_items = []
        if similar_items:
            top_item_ids = [item['metadata']['id'] for item in similar_items[:3]]
            related_items = self.get_related_items(top_item_ids)
        
        # Generate summary
        summary = self.search_summary(similar_items, related_items)
        print(f"SUMMARY: {summary}")
        
        return similar_items, related_items
    
    def generate_response(self, user_query, similar_items, related_items):
        """Generate AI response using OpenRouter with structured context"""
        # Format vector context
        vec_context = []
        for item in similar_items:
            meta = item['metadata']
            score = item.get('score', 0)
            vec_context.append(f"- {meta.get('name', '')} ({meta.get('type', '')}) in {meta.get('city', 'Vietnam')} [similarity: {score:.3f}]")
        
        # Format graph context
        graph_context = []
        for fact in related_items:
            graph_context.append(f"- {fact['target_name']} ({fact['relation']} from {fact['source']}): {fact['target_desc']}")
        
        system_prompt = (
            "You are a helpful Vietnam travel assistant with access to semantic search and knowledge graph data. "
            "Follow this chain of thought:\n"
            "1. ANALYZE: What type of travel experience is the user seeking?\n"
            "2. MATCH: Which locations from the search results best fit their needs?\n"
            "3. CONNECT: What related places or activities enhance the experience?\n"
            "4. RECOMMEND: Provide specific, actionable suggestions with reasoning.\n"
            "Be specific, cite actual places, and explain why each recommendation fits their query."
        )
        
        user_prompt = f"""User query: {user_query}

Top semantic matches:
{chr(10).join(vec_context[:5])}

Related places and connections:
{chr(10).join(graph_context[:10])}

Based on the above context, provide a helpful response with specific recommendations."""

        try:
            response = self.llm_client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=600,
                temperature=0.2
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Sorry, I encountered an error generating the response: {e}"
    
    async def chat_async(self, user_query):
        """Async main chat function with parallel processing"""
        print(f"\nSearching for: {user_query}")
        
        # Get RAG context with parallel processing
        similar_items, related_items = await self.get_rag_context_async(user_query)
        
        # Generate AI response
        print("Generating response...")
        response = self.generate_response(user_query, similar_items, related_items)
        
        return response
    
    def chat(self, user_query):
        """Main chat function (sync version)"""
        print(f"\nSearching for: {user_query}")
        
        # Get RAG context
        similar_items, related_items = self.get_rag_context(user_query)
        
        # Generate AI response
        print("Generating response...")
        response = self.generate_response(user_query, similar_items, related_items)
        
        return response

async def main_async():
    print("Vietnam Travel Chatbot (Async Mode)")
    print("=" * 50)
    print("Ask me anything about Vietnam travel!")
    print("Type 'quit' to exit\n")
    
    chatbot = VietnamTravelChatbot()
    
    try:
        while True:
            user_input = input("Enter your travel question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"Thanks for using Vietnam Travel Chatbot! Cache hits: {len(chatbot.embedding_cache)}")
                break
            
            if not user_input:
                continue
            
            # Get AI response with async processing
            response = await chatbot.chat_async(user_input)
            
            print(f"\nAI Response:")
            print("-" * 30)
            print(response)
            print(f"\nCache size: {len(chatbot.embedding_cache)} embeddings")
            print("\n" + "=" * 50 + "\n")
    
    except KeyboardInterrupt:
        print("\nGoodbye!")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        chatbot.close()

def main():
    print("Vietnam Travel Chatbot")
    print("=" * 50)
    print("Ask me anything about Vietnam travel!")
    print("Type 'quit' to exit\n")
    
    chatbot = VietnamTravelChatbot()
    
    try:
        while True:
            user_input = input("Enter your travel question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"Thanks for using Vietnam Travel Chatbot! Cache hits: {len(chatbot.embedding_cache)}")
                break
            
            if not user_input:
                continue
            
            # Get AI response
            response = chatbot.chat(user_input)
            
            print(f"\nAI Response:")
            print("-" * 30)
            print(response)
            print(f"\nCache size: {len(chatbot.embedding_cache)} embeddings")
            print("\n" + "=" * 50 + "\n")
    
    except KeyboardInterrupt:
        print("\nGoodbye!")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        chatbot.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--async":
        asyncio.run(main_async())
    else:
        main()