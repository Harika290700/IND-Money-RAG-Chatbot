"""Phase 1: Query the RAG index. Every answer prints the source URL(s) the information came from."""
# Use pysqlite3 so Chroma gets SQLite >= 3.35 on systems with older bundled sqlite3
try:
    import pysqlite3
    import sys
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import sys

from .rag import ask


def main():
    if len(sys.argv) < 2:
        print("Usage: python query.py \"Your question about mutual funds\"")
        print("Example: python query.py \"What is the expense ratio of SBI Contra Fund?\"")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    answer, sources = ask(query)

    print("\n--- Answer ---\n")
    print(answer)

    print("\n--- Source URL(s) (information is from these pages) ---")
    if not sources:
        print("  (no sources)")
    else:
        for s in sources:
            url = s.get("url", "")
            fund = s.get("fund_name", "")
            if url and url != "N/A":
                print(f"  {url}")
                if fund:
                    print(f"    Fund: {fund}")
            elif fund:
                print(f"  Fund: {fund}")


if __name__ == "__main__":
    main()
