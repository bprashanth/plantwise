from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
import os
import pandas as pd
import rasterio
import concurrent.futures
from typing import Optional
from fastapi.responses import FileResponse

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic model for request validation
class QueryRequest(BaseModel):
    latitude: float
    longitude: float
    min_probability: float = Field(..., alias="minProbability")


# Load data (same as Flask version)
auc_file = 'auc_and_contributions.csv'
auc_data = pd.read_csv(auc_file)
species_auc_map = dict(zip(auc_data['Species'], auc_data['Test AUC']))
species_latitude_ranges = {}

presence_folder = "sp_data_final"
for csv_file in os.listdir(presence_folder):
    if csv_file.endswith('.csv'):
        species_name = os.path.splitext(csv_file)[0]
        csv_path = os.path.join(presence_folder, csv_file)
        presence_data = pd.read_csv(csv_path)
        species_latitude_ranges[species_name] = {
            'max': presence_data['Latitude'].max(),
            'min': presence_data['Latitude'].min()
        }


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <head>
            <title>Species Habitat API</title>
        </head>
        <body>
            <h1>API Documentation available at /docs</h1>
        </body>
    </html>
    """


@app.post("/api/get-results")
async def get_results(query: QueryRequest):
    results = []
    results_folder = 'tif_data_final'
    tif_files = [os.path.join(results_folder, f)
                 for f in os.listdir(results_folder)
                 if f.endswith('.tif')]
    # print(tif_files)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(
                process_tif_file,
                tif_file,
                query.latitude,
                query.longitude,
                query.min_probability,
                species_latitude_ranges
            ): tif_file for tif_file in tif_files
        }

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    results.sort(key=lambda x: x['probability'], reverse=True)
    # print(results)
    return JSONResponse(content=results)


# Add this new endpoint after your existing endpoints
@app.get("/api/species/{species}/map")
async def get_species_map(species: str):
    """
    Returns the PNG map for a species' predictions
    """
    # Sanitize input and construct filename
    safe_species = species.replace("/", "_").replace("\\", "_")
    image_path = os.path.join('prediction_maps', f'{safe_species}_map.png')

    # print(f"DEBUG | Requested species: {species}")
    # print(f"DEBUG | Safe species: {safe_species}")
    # print(f"DEBUG | Looking for: {os.path.abspath(image_path)}")
    # print(f"DEBUG | Available files in prediction_maps: {os.listdir('prediction_maps')}")

    # Check if file exists
    if not os.path.exists(image_path):
        raise HTTPException(
            status_code=404,
            detail="Map not found for this species"
        )

    return FileResponse(image_path, media_type="image/png")


# Keep these functions same as Flask version
def process_tif_file(tif_file, latitude, longitude, min_probability, species_latitude_ranges):
    species = os.path.basename(tif_file).replace('.tif', '')

    # print(species)

    # Check if latitude is within range for this species
    lat_range = species_latitude_ranges.get(species)
    if lat_range:
        if latitude < lat_range['min'] or latitude > lat_range['max']:
            return None

    probability = get_probability_from_tif(tif_file, float(longitude), latitude)

    if probability is not None and probability >= float(min_probability) / 100:
        # Get the AUC for the species from the CSV data
        auc_value = species_auc_map.get(species, None)

        # If AUC is found, return the result
        if auc_value is not None:
            return {
                'species': species,
                'probability': int(probability * 100),
                'auc': auc_value
            }
    return None


def get_probability_from_tif(tif_file, x, y):
    with rasterio.open(tif_file) as src:
        transform = src.transform
        px, py = ~transform * (x, y)
        band = src.read(1)
        if 0 <= px < src.width and 0 <= py < src.height:
            return band[int(py), int(px)]
        return None

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
