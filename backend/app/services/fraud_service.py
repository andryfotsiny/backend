# app/services/fraud_service.py
import pandas as pd
import io
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.fraud import FraudulentNumber, FraudulentDomain, FraudType
from app.schemas.business import ImportResult

logger = logging.getLogger(__name__)

VALID_FRAUD_TYPES = {ft.value for ft in FraudType}


class FraudService:

    async def import_phones_from_csv(
        self, file_content: bytes, db: AsyncSession
    ) -> ImportResult:
        try:
            df = pd.read_csv(io.BytesIO(file_content))
            df.columns = [c.strip().lower() for c in df.columns]

            required = {"phone_number", "country_code", "fraud_type", "confidence_score"}
            missing = required - set(df.columns)
            if missing:
                return ImportResult(
                    success_count=0,
                    failure_count=0,
                    errors=[f"Colonnes manquantes : {', '.join(missing)}"],
                )

            df["phone_number"] = df["phone_number"].astype(str).str.strip()
            df["country_code"] = df["country_code"].astype(str).str.strip().str.upper()
            df["fraud_type"] = df["fraud_type"].astype(str).str.strip().str.lower()
            df["confidence_score"] = pd.to_numeric(df["confidence_score"], errors="coerce")

            if "source" not in df.columns:
                df["source"] = "import_csv"
            if "verified" not in df.columns:
                df["verified"] = False

            invalid_types = df[~df["fraud_type"].isin(VALID_FRAUD_TYPES)]
            if not invalid_types.empty:
                bad = invalid_types["fraud_type"].unique().tolist()
                return ImportResult(
                    success_count=0,
                    failure_count=len(invalid_types),
                    errors=[f"fraud_type invalide(s) : {bad}. Valeurs acceptées : {list(VALID_FRAUD_TYPES)}"],
                )

            invalid_score = df[df["confidence_score"].isna() | (df["confidence_score"] < 0) | (df["confidence_score"] > 1)]
            if not invalid_score.empty:
                return ImportResult(
                    success_count=0,
                    failure_count=len(invalid_score),
                    errors=["confidence_score doit être un float entre 0 et 1"],
                )

            initial_count = len(df)
            df = df.drop_duplicates(subset=["phone_number"], keep="first")
            internal_duplicates = initial_count - len(df)

            now = datetime.utcnow()
            records = []
            for _, row in df.iterrows():
                records.append({
                    "phone_number": row["phone_number"],
                    "country_code": row["country_code"],
                    "fraud_type": row["fraud_type"],
                    "confidence_score": float(row["confidence_score"]),
                    "report_count": 1,
                    "verified": bool(row.get("verified", False)),
                    "source": str(row.get("source", "import_csv")),
                    "first_reported": now,
                    "last_reported": now,
                })

            if not records:
                return ImportResult(
                    success_count=0,
                    skipped_count=internal_duplicates,
                    failure_count=0,
                    errors=["Aucun enregistrement valide trouvé"],
                )

            batch_size = 500
            inserted_count = 0
            processed = 0

            for i in range(0, len(records), batch_size):
                batch = records[i: i + batch_size]
                try:
                    stmt = pg_insert(FraudulentNumber).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["phone_number"],
                        set_={
                            "fraud_type": stmt.excluded.fraud_type,
                            "confidence_score": stmt.excluded.confidence_score,
                            "last_reported": stmt.excluded.last_reported,
                            "source": stmt.excluded.source,
                            "verified": stmt.excluded.verified,
                        },
                    )
                    result = await db.execute(stmt)
                    await db.commit()
                    inserted_count += result.rowcount if result.rowcount > 0 else len(batch)
                    processed += len(batch)
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Batch error phones import: {e}")
                    return ImportResult(
                        success_count=inserted_count,
                        skipped_count=internal_duplicates,
                        failure_count=len(records) - processed,
                        errors=[f"Erreur batch à la ligne {processed} : {str(e)}"],
                    )

            return ImportResult(
                success_count=inserted_count,
                skipped_count=internal_duplicates,
                failure_count=0,
            )

        except Exception as e:
            logger.error(f"import_phones_from_csv error: {e}")
            return ImportResult(success_count=0, failure_count=0, errors=[str(e)])

    async def import_domains_from_csv(
        self, file_content: bytes, db: AsyncSession
    ) -> ImportResult:
        try:
            df = pd.read_csv(io.BytesIO(file_content))
            df.columns = [c.strip().lower() for c in df.columns]

            required = {"domain", "reputation_score"}
            missing = required - set(df.columns)
            if missing:
                return ImportResult(
                    success_count=0,
                    failure_count=0,
                    errors=[f"Colonnes manquantes : {', '.join(missing)}"],
                )

            df["domain"] = df["domain"].astype(str).str.strip().str.lower()
            df["reputation_score"] = pd.to_numeric(df["reputation_score"], errors="coerce")

            if "phishing_type" not in df.columns:
                df["phishing_type"] = None

            invalid_score = df[df["reputation_score"].isna() | (df["reputation_score"] < 0) | (df["reputation_score"] > 1)]
            if not invalid_score.empty:
                return ImportResult(
                    success_count=0,
                    failure_count=len(invalid_score),
                    errors=["reputation_score doit être un float entre 0 et 1"],
                )

            initial_count = len(df)
            df = df.drop_duplicates(subset=["domain"], keep="first")
            internal_duplicates = initial_count - len(df)

            now = datetime.utcnow()
            records = []
            for _, row in df.iterrows():
                records.append({
                    "domain": row["domain"],
                    "phishing_type": row.get("phishing_type") if pd.notna(row.get("phishing_type")) else None,
                    "reputation_score": float(row["reputation_score"]),
                    "first_seen": now,
                    "blocked_count": 0,
                })

            if not records:
                return ImportResult(
                    success_count=0,
                    skipped_count=internal_duplicates,
                    failure_count=0,
                    errors=["Aucun enregistrement valide trouvé"],
                )

            batch_size = 500
            inserted_count = 0
            processed = 0

            for i in range(0, len(records), batch_size):
                batch = records[i: i + batch_size]
                try:
                    stmt = pg_insert(FraudulentDomain).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["domain"],
                        set_={
                            "phishing_type": stmt.excluded.phishing_type,
                            "reputation_score": stmt.excluded.reputation_score,
                        },
                    )
                    result = await db.execute(stmt)
                    await db.commit()
                    inserted_count += result.rowcount if result.rowcount > 0 else len(batch)
                    processed += len(batch)
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Batch error domains import: {e}")
                    return ImportResult(
                        success_count=inserted_count,
                        skipped_count=internal_duplicates,
                        failure_count=len(records) - processed,
                        errors=[f"Erreur batch à la ligne {processed} : {str(e)}"],
                    )

            return ImportResult(
                success_count=inserted_count,
                skipped_count=internal_duplicates,
                failure_count=0,
            )

        except Exception as e:
            logger.error(f"import_domains_from_csv error: {e}")
            return ImportResult(success_count=0, failure_count=0, errors=[str(e)])


fraud_service = FraudService()