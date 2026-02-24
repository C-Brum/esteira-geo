"""
CSV/GeoJSON to GeoParquet Converter - Silver Layer

Converte arquivos CSV e GeoJSON da camada Bronze para GeoParquet na camada Silver.
Normaliza dados, valida geometrias e padroniza tipos de dados.

Suporta:
  - CSV com colunas de latitude/longitude → GeoParquet com geometria Point
  - GeoJSON → GeoParquet com preservação de geometrias
  - Múltiplos arquivos de entrada
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional, List
import pyarrow.parquet as pq

# Adicionar diretório pai ao path para imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    SAMPLE_DATA_DIR, S3_SILVER_PREFIX,
    AWS_S3_SILVER_BUCKET, USE_MINIO, USE_S3, STORAGE_MODE,
    AWS_ENDPOINT_URL, LOCAL_SILVER_PATH
)

logger = logging.getLogger(__name__)


class CSVGeoJSONToGeoParquetConverter:
    """Converter para CSV/GeoJSON → GeoParquet"""
    
    def __init__(self):
        self.data_dir = SAMPLE_DATA_DIR
        self.silver_path = LOCAL_SILVER_PATH
        
    def convert_csv_to_geodataframe(self, csv_file: str, lat_col: str = 'latitude', 
                                    lon_col: str = 'longitude', crs: str = 'EPSG:4326') -> gpd.GeoDataFrame:
        """
        Converte CSV com colunas lat/lon para GeoDataFrame
        
        Args:
            csv_file: Caminho do arquivo CSV
            lat_col: Nome da coluna de latitude
            lon_col: Nome da coluna de longitude
            crs: Sistema de coordenadas
            
        Returns:
            GeoDataFrame com geometria Point
        """
        logger.info(f"Lendo CSV: {csv_file}")
        
        df = pd.read_csv(csv_file)
        
        # Validar colunas obrigatórias
        if lat_col not in df.columns or lon_col not in df.columns:
            raise ValueError(f"Colunas '{lat_col}' ou '{lon_col}' não encontradas no CSV")
        
        # Criar geometria Point
        geometry = gpd.points_from_xy(df[lon_col], df[lat_col])
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
        
        # Remover colunas de coordenadas originais (agora são parte da geometria)
        gdf = gdf.drop(columns=[lat_col, lon_col])
        
        return gdf
    
    def convert_geojson_to_geodataframe(self, geojson_file: str) -> gpd.GeoDataFrame:
        """
        Converte GeoJSON para GeoDataFrame
        
        Args:
            geojson_file: Caminho do arquivo GeoJSON
            
        Returns:
            GeoDataFrame
        """
        logger.info(f"Lendo GeoJSON: {geojson_file}")
        gdf = gpd.read_file(geojson_file)
        return gdf
    
    def normalize_dataframe(self, gdf: gpd.GeoDataFrame, source_type: str) -> gpd.GeoDataFrame:
        """
        Normaliza GeoDataFrame (tipos de dados, timestamps, validação)
        
        Args:
            gdf: GeoDataFrame a normalizar
            source_type: Tipo de fonte ('csv' ou 'geojson')
            
        Returns:
            GeoDataFrame normalizado
        """
        logger.info(f"Normalizando {source_type.upper()} (linhas: {len(gdf)})")
        
        # Validar geometrias
        gdf['geometry'] = gdf['geometry'].apply(lambda x: x if x.is_valid else x.buffer(0))
        
        # Padronizar tipos de dados
        for col in gdf.columns:
            if col == 'geometry':
                continue
                
            # Detectar e converter datas
            if gdf[col].dtype == 'object':
                try:
                    gdf[col] = pd.to_datetime(gdf[col], errors='coerce')
                    # Se a conversão funcionou para alguns valores, manter como datetime
                    if gdf[col].notna().sum() > 0:
                        logger.debug(f"Coluna '{col}' convertida para datetime")
                        continue
                except:
                    pass
            
            # Converter strings para lowercase (padronização)
            if gdf[col].dtype == 'object' and gdf[col].str.len().max() < 100:
                gdf[col] = gdf[col].apply(lambda x: x.lower() if isinstance(x, str) else x)
        
        # Adicionar metadados
        gdf['_processed_date'] = datetime.now().isoformat()
        gdf['_source_type'] = source_type
        gdf['_data_quality'] = 'validated'
        
        return gdf
    
    def save_to_geoparquet(self, gdf: gpd.GeoDataFrame, output_file: str) -> None:
        """
        Salva GeoDataFrame em formato GeoParquet
        
        Args:
            gdf: GeoDataFrame a salvar
            output_file: Caminho do arquivo de saída
        """
        logger.info(f"Salvando GeoParquet: {output_file}")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        gdf.to_parquet(output_file)
        
        # Verificar e logar informações
        file_size = Path(output_file).stat().st_size / (1024 * 1024)
        logger.info(f"GeoParquet salvo com sucesso: {file_size:.2f} MB")
    
    def process_csv_file(self, csv_file: str, output_file: str) -> gpd.GeoDataFrame:
        """
        Processa um arquivo CSV completo (leitura, normalização, salvamento)
        
        Args:
            csv_file: Arquivo CSV de entrada
            output_file: Arquivo GeoParquet de saída
            
        Returns:
            GeoDataFrame processado
        """
        logger.info(f"Processando CSV: {csv_file}")
        
        # Converter
        gdf = self.convert_csv_to_geodataframe(csv_file)
        
        # Normalizar
        gdf = self.normalize_dataframe(gdf, 'csv')
        
        # Salvar
        self.save_to_geoparquet(gdf, output_file)
        
        logger.info(f"CSV processado: {len(gdf)} registros")
        return gdf
    
    def process_geojson_file(self, geojson_file: str, output_file: str) -> gpd.GeoDataFrame:
        """
        Processa um arquivo GeoJSON completo (leitura, normalização, salvamento)
        
        Args:
            geojson_file: Arquivo GeoJSON de entrada
            output_file: Arquivo GeoParquet de saída
            
        Returns:
            GeoDataFrame processado
        """
        logger.info(f"Processando GeoJSON: {geojson_file}")
        
        # Converter
        gdf = self.convert_geojson_to_geodataframe(geojson_file)
        
        # Normalizar
        gdf = self.normalize_dataframe(gdf, 'geojson')
        
        # Salvar
        self.save_to_geoparquet(gdf, output_file)
        
        logger.info(f"GeoJSON processado: {len(gdf)} registros")
        return gdf
    
    def process_all_files(self) -> dict:
        """
        Processa todos os arquivos CSV/GeoJSON encontrados no diretório de dados
        
        Returns:
            Dicionário com resultados (arquivo → GeoDataFrame)
        """
        results = {}
        
        # Processar CSVs
        csv_files = list(self.data_dir.glob('*.csv'))
        logger.info(f"Encontrados {len(csv_files)} arquivos CSV")
        
        for csv_file in csv_files:
            try:
                output_file = self.silver_path / f"{csv_file.stem}.parquet"
                gdf = self.process_csv_file(str(csv_file), str(output_file))
                results[csv_file.name] = {
                    'status': 'success',
                    'geodataframe': gdf,
                    'records': len(gdf),
                    'output': str(output_file)
                }
            except Exception as e:
                logger.error(f"Erro processando {csv_file.name}: {str(e)}")
                results[csv_file.name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Processar GeoJSONs
        geojson_files = list(self.data_dir.glob('*.geojson'))
        logger.info(f"Encontrados {len(geojson_files)} arquivos GeoJSON")
        
        for geojson_file in geojson_files:
            try:
                output_file = self.silver_path / f"{geojson_file.stem}.parquet"
                gdf = self.process_geojson_file(str(geojson_file), str(output_file))
                results[geojson_file.name] = {
                    'status': 'success',
                    'geodataframe': gdf,
                    'records': len(gdf),
                    'output': str(output_file)
                }
            except Exception as e:
                logger.error(f"Erro processando {geojson_file.name}: {str(e)}")
                results[geojson_file.name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
    
    def get_summary(self, results: dict) -> dict:
        """
        Gera resumo dos processamentos
        
        Args:
            results: Dicionário de resultados
            
        Returns:
            Resumo com estatísticas
        """
        summary = {
            'total_files': len(results),
            'successful': sum(1 for r in results.values() if r['status'] == 'success'),
            'failed': sum(1 for r in results.values() if r['status'] == 'error'),
            'total_records': sum(r.get('records', 0) for r in results.values() if r['status'] == 'success'),
            'details': results
        }
        return summary


def run_conversion():
    """Executa conversão CSV/GeoJSON → GeoParquet"""
    
    logger.info("=" * 80)
    logger.info("INICIANDO CONVERSÃO CSV/GeoJSON → GeoParquet")
    logger.info("=" * 80)
    
    converter = CSVGeoJSONToGeoParquetConverter()
    results = converter.process_all_files()
    summary = converter.get_summary(results)
    
    # Logar resumo
    logger.info("=" * 80)
    logger.info("RESUMO DA CONVERSÃO")
    logger.info("=" * 80)
    logger.info(f"Total de arquivos: {summary['total_files']}")
    logger.info(f"Sucesso: {summary['successful']}")
    logger.info(f"Falhas: {summary['failed']}")
    logger.info(f"Total de registros: {summary['total_records']}")
    logger.info("=" * 80)
    
    return summary


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    summary = run_conversion()
    
    # Log detalhes de sucesso
    for filename, result in summary['details'].items():
        if result['status'] == 'success':
            logger.info(f"✓ {filename}: {result['records']} registros → {result['output']}")
        else:
            logger.error(f"✗ {filename}: {result['error']}")
