import pandas as pd
import io
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.business import Business as BusinessModel
from app.schemas.business import ImportResult
from app.services.geo_service import extract_country_and_prefix

logger = logging.getLogger(__name__)


class BusinessService:
    async def import_from_file(
        self, file_content: bytes, file_type: str, db: AsyncSession
    ) -> ImportResult:
        try:
            if file_type == "csv":
                logger.info("Starting CSV parsing")
                df = pd.read_csv(io.BytesIO(file_content))
            elif file_type in ["xlsx", "xls"]:
                logger.info(
                    "Starting Excel parsing (this may take a while for large files)"
                )
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                return ImportResult(
                    success_count=0,
                    failure_count=0,
                    errors=[f"Unsupported file type: {file_type}"],
                )

            column_mapping = {
                "nomination": "nomination",
                "adresse": "adresse",
                "code_postal": "code_postale",
                "code_postale": "code_postale",
                "cp": "code_postale",
                "ville": "ville",
                "tel": "tel",
                "act": "act",
                "nom": "nom",
                "code_pays": "code_pays",
            }

            existing_cols = {
                col: column_mapping[col.lower()]
                for col in df.columns
                if col.lower() in column_mapping
            }
            df = df.rename(columns=existing_cols)

            if "nomination" not in df.columns:
                return ImportResult(
                    success_count=0,
                    failure_count=0,
                    errors=["Required column 'NOMINATION' not found in file"],
                )

            # Initialise les colonnes si absentes
            if "code_pays" not in df.columns:
                df["code_pays"] = None
            if "prefixe" not in df.columns:
                df["prefixe"] = None

            # Normalise le tel avant traitement
            if "tel" in df.columns:
                df["tel"] = df["tel"].astype(str).str.strip()

            # Détection code_pays + prefixe via geo_service
            geo_results = df.apply(extract_country_and_prefix, axis=1)
            df["code_pays"] = geo_results.apply(lambda x: x[0])
            df["prefixe"] = geo_results.apply(lambda x: x[1])

            internal_duplicates = 0
            if "tel" in df.columns:
                initial_count = len(df)
                df = df.drop_duplicates(subset=["tel"], keep="first")
                internal_duplicates = initial_count - len(df)
                if internal_duplicates > 0:
                    logger.info(
                        f"Removed {internal_duplicates} duplicates within the file"
                    )

            df = df.astype(str)
            df = df.replace("nan", None)
            df = df.where(pd.notnull(df), None)

            records = df.to_dict("records")

            if not records:
                return ImportResult(
                    success_count=0,
                    skipped_count=internal_duplicates,
                    failure_count=0,
                    errors=["No unique records found in file"],
                )

            batch_size = 1000
            success_count = 0
            inserted_count = 0
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                try:
                    stmt = pg_insert(BusinessModel).values(batch)
                    stmt = stmt.on_conflict_do_nothing(index_elements=["tel"])

                    result = await db.execute(stmt)
                    await db.commit()

                    inserted_count += result.rowcount if result.rowcount > 0 else 0
                    success_count += len(batch)
                except Exception as batch_error:
                    await db.rollback()
                    logger.error(
                        f"Error in batch {i // batch_size}: {str(batch_error)}"
                    )
                    return ImportResult(
                        success_count=inserted_count,
                        skipped_count=internal_duplicates
                        + (success_count - inserted_count),
                        failure_count=len(records) - success_count,
                        errors=[
                            f"Batch error at row {success_count}: {str(batch_error)}"
                        ],
                    )

            skipped_count = len(records) - inserted_count + internal_duplicates
            return ImportResult(
                success_count=inserted_count,
                skipped_count=skipped_count,
                failure_count=0,
            )

        except Exception as e:
            logger.error(f"Error importing business data: {str(e)}")
            return ImportResult(success_count=0, failure_count=0, errors=[str(e)])

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> tuple[List[BusinessModel], int]:
        from sqlalchemy import or_, select, func

        query = select(BusinessModel)

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    BusinessModel.nomination.ilike(search_filter),
                    BusinessModel.ville.ilike(search_filter),
                    BusinessModel.act.ilike(search_filter),
                    BusinessModel.tel.ilike(search_filter),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all(), total_count

    async def update(
        self, db: AsyncSession, *, business_id: int, obj_in: dict
    ) -> Optional[BusinessModel]:
        from sqlalchemy import update

        update_data = {k: v for k, v in obj_in.items() if v is not None}
        if not update_data:
            from sqlalchemy import select

            query = select(BusinessModel).where(BusinessModel.id == business_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()

        stmt = (
            update(BusinessModel)
            .where(BusinessModel.id == business_id)
            .values(**update_data)
            .returning(BusinessModel)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    async def remove(self, db: AsyncSession, *, business_id: int) -> bool:
        from sqlalchemy import delete

        stmt = delete(BusinessModel).where(BusinessModel.id == business_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0


business_service = BusinessService()