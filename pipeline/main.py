#!/usr/bin/env python3
"""
Pipeline Principal - Esteira Geo
Orquestrador de batimento geográfico de enchentes em Porto Alegre

Arquitetura Medallion:
  Bronze -> Silver -> Gold -> PostGIS -> Flask
  
Fluxo:
  1. Bronze: Cria/carrega dados de exemplo (áreas enchente + cidadãos)
  2. Silver: Normaliza e valida dados
  3. Gold: Realiza batimento geográfico (spatial join)
  4. PostGIS: Importa dados em RDS
  5. Flask: Disponibiliza na camada de apresentação
"""

import logging
import sys
from datetime import datetime

# Importar módulos do pipeline
from etl.bronze_loader import load_sample_data
from etl.silver_processor import process_silver
from etl.gold_processor import process_gold
from etl.postgis_loader import load_to_postgis
from config import (
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, ALL_CITIZENS_FILE
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Executa o pipeline completo"""
    
    logger.info("\n")
    logger.info("#" * 70)
    logger.info("# ESTEIRA GEO - Pipeline de Batimento Geográfico")
    logger.info("# Caso de Uso: Enchentes em Porto Alegre - Rio Grande do Sul")
    logger.info(f"# Data/Hora: {datetime.now()}")
    logger.info("#" * 70)
    
    try:
        # BRONZE: Gerar dados de exemplo
        logger.info("\n[1/5] BRONZE - Carregando dados...")
        flooding_bronze, citizens_bronze = load_sample_data()
        logger.info(f"✓ Bronze: {len(flooding_bronze)} áreas + {len(citizens_bronze)} cidadãos")
        
        # SILVER: Normalizar
        logger.info("\n[2/5] SILVER - Normalizando...")
        flooding_silver, citizens_silver = process_silver()
        logger.info(f"✓ Silver: {len(flooding_silver)} áreas + {len(citizens_silver)} cidadãos")
        
        # GOLD: Processamento geoespacial
        logger.info("\n[3/5] GOLD - Batimento geográfico...")
        affected, unaffected, all_summary = process_gold()
        logger.info(f"✓ Gold: {len(affected)} afetados + {len(unaffected)} não afetados")
        
        # POSTGIS: Carregar banco de dados
        logger.info("\n[4/5] POSTGIS - Importar dados...")
        success = load_to_postgis()
        if not success:
            logger.warning("⚠ PostGIS load falhou (banco pode estar offline)")
        
        # Resumo final
        logger.info("\n[5/5] RESUMO FINAL")
        logger.info("=" * 70)
        logger.info(f"✓ PIPELINE CONCLUÍDO COM SUCESSO!")
        logger.info(f"  Cidadãos Atingidos: {len(affected)}")
        logger.info(f"  Cidadãos Não Atingidos: {len(unaffected)}")
        logger.info(f"  Total Avaliado: {len(all_summary)}")
        logger.info(f"  Percentual Atingido: {(len(affected)/len(all_summary)*100):.1f}%")
        logger.info(f"\nArquivos Gold gerados:")
        logger.info(f"  1. {AFFECTED_CITIZENS_FILE}")
        logger.info(f"  2. {UNAFFECTED_CITIZENS_FILE}")
        logger.info(f"  3. {ALL_CITIZENS_FILE}")
        logger.info("=" * 70)
        
        logger.info("\n🎉 Próximas etapas:")
        logger.info("   1. Dados importados no PostGIS (se banco online)")
        logger.info("   2. Acessar dashboard Flask em: http://<VM_IP>/")
        logger.info("   3. Visualizar geometrias e estatísticas")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n✗ ERRO NO PIPELINE: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
