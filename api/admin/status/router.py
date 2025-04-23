from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import exc, text
from sqlalchemy.orm import Session

from api.admin.status.models import KnowledgeStatus, PostgresStatus, SystemStatus
from db.database import get_db
from services.uni import RAG_AUTHORIZATION, rag_service

router = APIRouter(
    prefix="/status",
)


@router.get("/", response_model=SystemStatus)
async def get_status(db: Session = Depends(get_db)):
    result = SystemStatus()

    try:
        db.execute(text("SELECT 1")).scalar()
        result.postgres_online = True
    except Exception:
        result.postgres_online = False

    system_status = rag_service.get_system_status(authorization=RAG_AUTHORIZATION)
    result.knowledge_online = system_status is not None

    return result


@router.get("/knowledge", response_model=Optional[KnowledgeStatus])
async def get_knowledge_status():
    try:
        system_status = rag_service.get_system_status(authorization=RAG_AUTHORIZATION)
        return system_status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving knowledge system status: {str(e)}",
        )


@router.get("/postgres", response_model=PostgresStatus)
async def get_postgres_status(db: Session = Depends(get_db)):
    status = PostgresStatus(is_connected=False)

    try:
        version_result = db.execute(text("SELECT version();")).scalar()
        status.is_connected = True
        status.version = version_result

        uptime_result = db.execute(
            text(
                "SELECT date_trunc('second', current_timestamp - pg_postmaster_start_time()) as uptime;"
            )
        ).scalar()
        status.uptime = str(uptime_result)

        connection_stats = db.execute(
            text(
                """
            SELECT 
                count(*) as total_connections,
                sum(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active_connections,
                (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
            FROM pg_stat_activity;
        """
            )
        ).first()

        if connection_stats:
            status.current_connections = connection_stats[0]
            status.active_connections = connection_stats[1]
            status.max_connections = connection_stats[2]

            if status.max_connections:
                status.connection_usage_percent = (
                    status.current_connections / status.max_connections
                ) * 100

        db_size_result = db.execute(
            text(
                """
            SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;
        """
            )
        ).scalar()
        status.database_size = db_size_result

        tables_count = db.execute(
            text(
                """
            SELECT count(*) FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
        """
            )
        ).scalar()
        status.tables_count = tables_count

        detailed_stats = {}

        table_stats = db.execute(
            text(
                """
            SELECT
                schemaname,
                relname,
                seq_scan,
                seq_tup_read,
                idx_scan,
                idx_tup_fetch,
                n_tup_ins,
                n_tup_upd,
                n_tup_del,
                n_live_tup,
                n_dead_tup
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
            LIMIT 10;
        """
            )
        )

        detailed_stats["top_tables"] = [dict(row._mapping) for row in table_stats]

        status.detailed_stats = detailed_stats

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving database status: {str(e)}",
        )

    return status
