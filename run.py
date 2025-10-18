#!/usr/bin/env python3
"""
Main entry point for Vietnam Travel RAG System
Usage: python run.py [--async] [--setup]
"""
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Vietnam Travel RAG System")
    parser.add_argument("--async", action="store_true", help="Run in async mode")
    parser.add_argument("--setup", action="store_true", help="Run setup (upload data)")
    
    args = parser.parse_args()
    
    if args.setup:
        print("Running data setup...")
        print("1. Uploading to Pinecone...")
        import pinecone_upload
        pinecone_upload.main()
        
        print("2. Uploading to Neo4j...")
        import neo4j_upload
        neo4j_upload.main()
        
        print("Setup complete! You can now run the chat system.")
        
    else:
        print("Starting Vietnam Travel RAG System...")
        if args.async:
            import asyncio
            from hybrid_chat import main_async
            asyncio.run(main_async())
        else:
            from hybrid_chat import main
            main()

if __name__ == "__main__":
    main()