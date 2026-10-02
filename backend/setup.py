"""One-shot setup: generate data → ingest → train models.
Run: python setup.py
"""
import subprocess
import sys


def main():
    print("=" * 60)
    print("  RevOS — Setup Pipeline")
    print("=" * 60)

    # Step 1: Generate synthetic data
    print("\n[1/3] Generating synthetic data...")
    from generate_data import main as generate_data_main
    generate_data_main()

    # Step 2: Ingest into DB + ChromaDB
    print("\n[2/3] Ingesting data into database + vector store...", flush=True)
    from ingestion import ingest_all
    ingest_all()

    # Step 3: Train ML models
    print("\n[3/3] Training ML models...", flush=True)
    from database import SessionLocal
    from routes import train_models
    db = SessionLocal()
    try:
        result = train_models(db)
        print(f"\n[+] Training complete:", flush=True)
        print(f"  Deals scored: {result['deals_scored']}", flush=True)
        print(f"  High risk: {result['high_risk_count']}", flush=True)
        print(f"  Medium risk: {result['medium_risk_count']}", flush=True)
        print(f"  Forecast model: {result['forecast_model']}", flush=True)
    finally:
        db.close()

    print("\n" + "=" * 60, flush=True)
    print("  [+] Setup complete! Start the server:", flush=True)
    print("    python main.py", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
