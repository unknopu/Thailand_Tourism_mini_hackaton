import chromadb

# 1. เชื่อมต่อกับโฟลเดอร์ chroma_db ของเรา
client = chromadb.PersistentClient(path="./chroma_db")

# 2. ระบุชื่อคอลเลกชัน (Collection) ที่เราตั้งไว้
collection = client.get_collection(name="places_search_index")

# 3. ขอดูดข้อมูลทั้งหมดออกมาดู! (เอาแค่ 5 อันแรก)
print("🔍 ข้อมูลใน ChromaDB:")
results = collection.get(limit=5) 

# 4. พิมพ์ผลลัพธ์ออกมาดู
for i in range(len(results['ids'])):
    print(f"\n📍 ID: {results['ids'][i]}")
    print(f"📄 Text: {results['documents'][i][:100]}...") # โชว์แค่ 100 ตัวอักษรแรก
    print(f"🏷️ Meta: {results['metadatas'][i]}")