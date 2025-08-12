import os
import pandas as pd
import kagglehub
import logging
from flask import Flask, jsonify
from google.cloud import bigquery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy"}, 200

@app.route("/", methods=["GET"])
def run_etl():
    try:
        logger.info("Starting ETL process...")
        
        # Check for required environment variable
        dataset_id = os.environ.get("BIGQUERY_DATASET")
        if not dataset_id:
            logger.error("BIGQUERY_DATASET environment variable not set")
            return jsonify({"error": "BIGQUERY_DATASET environment variable not set"}), 500
            
        logger.info(f"Using BigQuery dataset: {dataset_id}")
        
        # Set up custom cache directory for kagglehub (Cloud Run allows writes only in /tmp)
        cache_dir = "/tmp/kaggle_cache"
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["KAGGLEHUB_CACHE"] = cache_dir
        logger.info(f"Using Kaggle cache directory: {cache_dir}")
        
        # Download dataset from Kaggle
        logger.info("Downloading dataset from Kaggle...")
        dataset_path = kagglehub.dataset_download("open-source-sports/baseball-databank")
        logger.info(f"Dataset downloaded to: {dataset_path}")

        # Initialize BigQuery client only when needed
        logger.info("Initializing BigQuery client...")
        bq_client = bigquery.Client()

        # Load CSV files to BigQuery
        logger.info("Loading CSV files to BigQuery...")
        for file_name in os.listdir(dataset_path):
            if file_name.endswith(".csv"):
                logger.info(f"Processing file: {file_name}")
                df = pd.read_csv(os.path.join(dataset_path, file_name))
                table_id = f"{dataset_id}.{file_name[:-4]}"
                logger.info(f"Loading to table: {table_id}")
                bq_client.load_table_from_dataframe(df, table_id).result()
                logger.info(f"Successfully loaded {file_name}")

        logger.info("ETL process completed successfully")
        return "✅ Dataset successfully loaded to BigQuery.", 200
    except Exception as exc:
        logger.error(f"Error in ETL process: {str(exc)}")
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
