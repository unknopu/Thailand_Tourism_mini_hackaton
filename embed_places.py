"""
Travel Place Embedding Script
=============================
This script creates a search index for a travel app by generating
embeddings from place data and storing them in ChromaDB.

Steps:
1. Check if places.csv exists
2. Read data from CSV
3. Create embeddings using BAAI/bge-m3 model
4. Store in ChromaDB with metadata
"""

# =============================================================================
# Step 1: Import required libraries
# =============================================================================

import csv          # For reading CSV files
import os           # For file/folder operations
from pathlib import Path  # For safe path handling

# LangChain with HuggingFace for embeddings
from langchain_huggingface import HuggingFaceEmbeddings

# ChromaDB for vector database storage
import chromadb
from chromadb.config import Settings


# =============================================================================
# Step 2: Define configuration constants
# =============================================================================

# Path to the input CSV file
CSV_FILE_PATH = "data/places.csv"

# Path to store the vector database
CHROMA_DB_PATH = "chroma_db"

# Name of the collection in ChromaDB
COLLECTION_NAME = "places_search_index"


# =============================================================================
# Step 3: Function to check if CSV file exists
# =============================================================================

def check_csv_exists(file_path):
    """
    Check if the places.csv file exists before starting.
    
    Parameters:
        file_path: Path to the CSV file
        
    Returns:
        True if file exists, False otherwise
    """
    if os.path.exists(file_path):
        print(f"✅ Found CSV file: {file_path}")
        return True
    else:
        print(f"❌ Error: CSV file not found at {file_path}")
        print("Please make sure places.csv exists in the data/ folder")
        return False


# =============================================================================
# Step 4: Function to read data from CSV
# =============================================================================

def read_places_csv(file_path):
    """
    Read place data from CSV file.
    
    Parameters:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries containing place data
    """
    places = []
    
    # Open and read the CSV file
    with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as file:
        csv_reader = csv.DictReader(file)
        
        # Loop through each row and store as dictionary
        for row in csv_reader:
            places.append(row)
    
    print(f"📖 Successfully read {len(places)} places from CSV")
    return places


# =============================================================================
# Step 5: Function to combine ALL columns into one text
# =============================================================================

def create_search_text(place):
    """
    Combine ALL columns from CSV into a single string for embedding.
    This ensures the search index includes all available information.
    
    Parameters:
        place: Dictionary containing place data
        
    Returns:
        Combined text string with all columns
    """
    # Extract ALL columns from the CSV
    name_th = place.get('name_th', '')       # Thai name
    name_en = place.get('name_en', '')        # English name
    province = place.get('province', '')      # Province
    region = place.get('region', '')          # Region (north, south, east, etc.)
    style = place.get('style', '')            # Style (nature, historical, beach, etc.)
    budget_range = place.get('budget_range', '')  # Budget (low, mid, high)
    crowd_level = place.get('crowd_level', '')    # Crowd level (1-10)
    hidden_gem_score = place.get('hidden_gem_score', '')  # Hidden gem score
    tags = place.get('tags', '')              # Tags/keywords
    description = place.get('description', '') # Full description
    
    # Combine ALL columns into one text for better search
    combined_text = (
        f"Thai Name: {name_th} | "
        f"English Name: {name_en} | "
        f"Province: {province} | "
        f"Region: {region} | "
        f"Style: {style} | "
        f"Budget Range: {budget_range} | "
        f"Crowd Level: {crowd_level} | "
        f"Hidden Gem Score: {hidden_gem_score} | "
        f"Tags: {tags} | "
        f"Description: {description}"
    )
    
    return combined_text


# =============================================================================
# Step 6: Function to create embeddings model
# =============================================================================

def create_embeddings_model():
    """
    Create and return the HuggingFace embeddings model.
    Uses BAAI/bge-m3 model which is good for multilingual search.
    
    Returns:
        HuggingFaceEmbeddings model object
    """
    print("🔄 Loading BAAI/bge-m3 embeddings model...")
    
    # Configure the embeddings model
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",  # Model from HuggingFace
        model_kwargs={
            'device': 'cpu'  # Use CPU (change to 'cuda' for GPU)
        },
        encode_kwargs={
            'normalize_embeddings': True  # Normalize vectors to length 1
        }
    )
    
    print("✅ Model loaded successfully!")
    return embeddings


# =============================================================================
# Step 7: Function to create and populate ChromaDB
# =============================================================================

def create_chroma_database(places, embeddings):
    """
    Create ChromaDB collection and add all place embeddings.
    
    Parameters:
        places: List of place dictionaries
        embeddings: The embeddings model to use
        
    Returns:
        The created collection object
    """
    # Initialize ChromaDB client with persistent storage
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # Delete existing collection to allow re-running the script
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print("🗑️ Removed existing collection")
    except:
        pass  # No existing collection
    
    # Create new collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Travel places search index"}
    )
    
    print(f"📦 Created collection: {COLLECTION_NAME}")
    
    # Prepare lists for ChromaDB
    ids = []           # Store place IDs
    documents = []    # Store combined text
    metadatas = []    # Store metadata for filtering
    
    print("🔄 Processing places and creating embeddings...")
    
    # Process each place
    for i, place in enumerate(places):
        # Create combined text for embedding
        search_text = create_search_text(place)
        
        # Add to lists
        ids.append(place['id'])
        documents.append(search_text)
        
        # Store ALL columns as metadata for filtering later
        metadatas.append({
            "id": place.get('id', ''),
            "name_th": place.get('name_th', ''),
            "name_en": place.get('name_en', ''),
            "province": place.get('province', ''),
            "region": place.get('region', ''),
            "style": place.get('style', ''),
            "budget_range": place.get('budget_range', ''),
            "crowd_level": int(place.get('crowd_level', 0)),
            "hidden_gem_score": float(place.get('hidden_gem_score', 0.0)),
            "tags": place.get('tags', ''),
            "description": place.get('description', '')
        })
        
        # Show progress
        if (i + 1) % 5 == 0:
            print(f"   Processed {i + 1}/{len(places)} places...")
    
    # Generate embeddings for all documents
    print("🔄 Generating embeddings with BAAI/bge-m3...")
    embedding_vectors = embeddings.embed_documents(documents)
    
    # Add everything to ChromaDB
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embedding_vectors
    )
    
    print(f"✅ Successfully added {len(ids)} places to database!")
    return collection


# =============================================================================
# Step 8: Function to test the search index
# =============================================================================

def test_search(collection, embeddings, query):
    """
    Test the search index with a sample query.
    
    Parameters:
        collection: ChromaDB collection
        embeddings: Embeddings model
        query: Search query string
    """
    print(f"\n🔍 Testing search with: '{query}'")
    print("-" * 50)
    
    # Create embedding for the query
    query_embedding = embeddings.embed_query(query)
    
    # Search the database
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,  # Return top 3 results
        include=["documents", "metadatas", "distances"]
    )
    
    # Display results with all metadata fields
    for i, (doc, meta, dist) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    )):
        similarity = 1 - dist  # Convert distance to similarity
        print(f"\n📍 Result {i+1}:")
        print(f"   ID: {meta['id']}")
        print(f"   Thai Name: {meta['name_th']}")
        print(f"   English Name: {meta['name_en']}")
        print(f"   Province: {meta['province']}")
        print(f"   Region: {meta['region']}")
        print(f"   Style: {meta['style']}")
        print(f"   Budget: {meta['budget_range']}")
        print(f"   Crowd Level: {meta['crowd_level']}")
        print(f"   Hidden Gem Score: {meta['hidden_gem_score']}")
        print(f"   Tags: {meta['tags']}")
        print(f"   Similarity: {similarity:.4f}")
        print(f"   Preview: {doc[:100]}...")


# =============================================================================
# Step 9: Main function - orchestrates the entire workflow
# =============================================================================

def main():
    """
    Main function that runs the complete embedding process.
    """
    print("=" * 60)
    print("🚀 Starting Travel Place Embedding Process")
    print("=" * 60)
    
    # Step 1: Check if CSV file exists
    print("\n📌 Step 1: Checking for places.csv...")
    if not check_csv_exists(CSV_FILE_PATH):
        return  # Exit if file not found
    
    # Step 2: Read data from CSV
    print("\n📌 Step 2: Reading data from CSV...")
    places = read_places_csv(CSV_FILE_PATH)
    
    # Step 3: Create embeddings model
    print("\n📌 Step 3: Loading BAAI/bge-m3 model...")
    embeddings = create_embeddings_model()
    
    # Step 4: Create ChromaDB and store embeddings
    print("\n📌 Step 4: Creating ChromaDB database...")
    collection = create_chroma_database(places, embeddings)
    
    # Step 5: Test the search index
    print("\n📌 Step 5: Testing search functionality...")
    test_queries = [
        "beautiful nature park",
        "historical cultural site"
    ]
    
    for query in test_queries:
        test_search(collection, embeddings, query)
    
    # Final summary
    print("\n" + "=" * 60)
    print("✅ Embedding process completed successfully!")
    print(f"📂 Vector database saved to: {CHROMA_DB_PATH}")
    print(f"📊 Total places indexed: {len(places)}")
    print("=" * 60)


# =============================================================================
# Step 10: Run the script
# =============================================================================

if __name__ == "__main__":
    main()