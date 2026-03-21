import { RAGClient } from './dist/clients/rag_client.js';
import { formatSearchResults } from './dist/utils/formatter.js';

async function runTests() {
  const client = new RAGClient("http://localhost:8000");
  try {
    console.log("==========================================");
    console.log("Testing semanticSearch ('加班費計算')...");
    const res1 = await client.semanticSearch("加班費計算", 2);
    console.log(formatSearchResults(res1.results));
    
    console.log("==========================================");
    console.log("Testing exactSearch ('勞動基準法 第 24 條')...");
    const res2 = await client.exactSearch("勞動基準法 第 24 條");
    console.log(formatSearchResults(res2.results));

    console.log("==========================================");
    console.log("Testing searchLaw ('勞基法')...");
    const res3 = await client.searchLaw("勞基法", false);
    console.log(formatSearchResults(res3.results));

    console.log("==========================================");
    console.log("All tests completed successfully.");
  } catch (err) {
    console.error("Test failed:", err);
    process.exit(1);
  }
}

runTests();
