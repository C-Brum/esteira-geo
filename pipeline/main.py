#!/usr/bin/env python3
"""
Pipeline Principal - Esteira Geo

Cenários suportados (determinados pelo conteúdo do bronze):

  Só áreas    → Silver(áreas) → PostGIS(áreas) → Flask mostra polígonos
  Só cidadãos → Silver(cidadãos) apenas — aguarda áreas para ir ao gold
  Ambos       → Silver → Gold → PostGIS(áreas + cidadãos) → Flask completo
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

ENGINE = os.getenv("ENGINE", "python").lower()

if ENGINE == "spark":
    from etl.spark.silver_processor import process_silver_spark as process_silver
    from etl.spark.gold_processor   import process_gold_spark   as process_gold
    from etl.spark.postgis_loader   import load_to_postgis_spark as load_to_postgis
else:
    from etl.silver_processor import process_silver
    from etl.gold_processor   import process_gold, silver_ready
    from etl.postgis_loader   import load_to_postgis

from config import (
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, ALL_CITIZENS_FILE,
    LOCAL_GOLD_USE_CASE,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("#" * 70)
    logger.info("# ESTEIRA GEO - Pipeline de Batimento Geográfico")
    logger.info(f"# Engine: {ENGINE.upper()} | {datetime.now()}")
    logger.info("#" * 70)

    try:
        # ── SILVER ──────────────────────────────────────────────────────────
        logger.info("\n[1] SILVER - Lendo bronze e normalizando...")
        try:
            silver = process_silver()
            has_flooding = 'flooding' in silver
            has_citizens = 'citizens' in silver
            if has_flooding:
                logger.info(f"  ✓ Áreas:    {len(silver['flooding'])} registros → silver")
            if has_citizens:
                logger.info(f"  ✓ Cidadãos: {len(silver['citizens'])} registros → silver")
        except RuntimeError as e:
            if "bronze" in str(e).lower():
                logger.info("  Bronze vazio — sincronizando PostGIS com estado atual do S3...")
                has_areas_silver, has_citizens_silver = silver_ready()
                load_to_postgis(sync_areas=has_areas_silver, sync_citizens=has_citizens_silver)
                return 0
            raise

        # ── GOLD ─────────────────────────────────────────────────────────────
        has_areas_silver, has_citizens_silver = silver_ready()

        if has_areas_silver and has_citizens_silver:
            logger.info("\n[2] GOLD - Batimento geográfico...")
            affected, unaffected, all_summary = process_gold()
            n_affected   = len(affected)
            n_unaffected = len(unaffected)
            n_total      = len(all_summary)
            logger.info(f"  ✓ {n_affected} afetados | {n_unaffected} não afetados | {n_total} total")

            logger.info("\n[3] POSTGIS - Sincronizando áreas + cidadãos...")
            load_to_postgis(sync_areas=True, sync_citizens=True)

            logger.info("\n" + "=" * 70)
            logger.info("✓ PIPELINE CONCLUÍDO — GOLD COMPLETO")
            logger.info(f"  Atingidos:     {n_affected} ({n_affected/n_total*100:.1f}%)")
            logger.info(f"  Não atingidos: {n_unaffected}")
            logger.info(f"  Total:         {n_total}")
            logger.info("=" * 70)

        elif has_areas_silver and not has_citizens_silver:
            logger.info("\n[2] GOLD - Pulado (sem cidadãos no silver)")
            logger.info("\n[3] POSTGIS - Sincronizando apenas áreas...")
            load_to_postgis(sync_areas=True, sync_citizens=False)

            logger.info("\n" + "=" * 70)
            logger.info("✓ PIPELINE CONCLUÍDO — ÁREAS DISPONÍVEIS NO FLASK")
            logger.info(f"  {len(silver['flooding'])} polígonos de enchente carregados")
            logger.info("  Aguardando upload de cidadãos para batimento completo")
            logger.info("=" * 70)

        else:
            # Só cidadãos — silver salvo, aguarda áreas
            logger.info("\n[2] GOLD - Pulado (sem áreas no silver)")
            logger.info("\n[3] POSTGIS - Pulado")
            logger.info("\n" + "=" * 70)
            logger.info("✓ PIPELINE CONCLUÍDO — CIDADÃOS NO SILVER")
            logger.info(f"  {len(silver['citizens'])} cidadãos normalizados e aguardando áreas")
            logger.info("  Faça upload de um arquivo de áreas para completar o batimento")
            logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"\n✗ ERRO NO PIPELINE: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
