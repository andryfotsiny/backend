import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    async def send_password_reset_email(self, recipient_email: str, reset_token: str) -> bool:
        """Envoie un email de réinitialisation de mot de passe."""
        reset_url = f"{settings.FRONTEND_HOST.rstrip('/')}/reset-password?token={quote(reset_token)}"
        subject = "Réinitialisation de votre mot de passe"
        sender_name = settings.EMAILS_FROM_NAME or settings.PROJECT_NAME
        sender_email = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER or "no-reply@localhost"
        logger.info(
            "[email] Préparation email reset to=%s from=%s smtp=%s:%s",
            recipient_email,
            sender_email,
            settings.SMTP_HOST,
            settings.SMTP_PORT,
        )
        plain_body = (
            f"Bonjour,\n\n"
            f"Nous avons reçu une demande de réinitialisation de votre mot de passe.\n"
            f"Cliquez sur le lien ci-dessous (ou copiez-collez-le dans votre navigateur) pour choisir un nouveau mot de passe:\n\n"
            f"{reset_url}\n\n"
            f"Ce lien expire dans {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n\n"
            f"✓ Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email en toute sécurité.\n\n"
            f"—\n"
            f"© 2026 DYLETH. Tous droits réservés.\n"
        )
        html_body = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
                    background-color: #f3f4f6;
                    margin: 0;
                    padding: 20px;
                    line-height: 1.6;
                    color: #1f2937;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
                    padding: 40px 20px;
                    text-align: center;
                    color: #ffffff;
                }}
                .logo {{
                    width: 80px;
                    height: 80px;
                    margin: 0 auto 20px;
                }}
                .logo img {{
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                }}
                .header-title {{
                    font-size: 28px;
                    margin: 0;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}
                .greeting {{
                    font-size: 16px;
                    margin-bottom: 20px;
                    color: #374151;
                }}
                .message {{
                    font-size: 14px;
                    margin-bottom: 30px;
                    color: #6b7280;
                }}
                .cta-button {{
                    display: inline-block;
                    background-color: #111827;
                    color: #ffffff;
                    padding: 16px 40px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 20px 0;
                    transition: background-color 0.3s ease;
                }}
                .cta-button:hover {{
                    background-color: #1f2937;
                }}
                .expiry {{
                    font-size: 12px;
                    color: #9ca3af;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                }}
                .security-notice {{
                    background-color: #f9fafb;
                    padding: 15px 20px;
                    margin-top: 20px;
                    border-left: 4px solid #10b981;
                    border-radius: 4px;
                    font-size: 12px;
                    color: #6b7280;
                }}
                .footer {{
                    background-color: #f9fafb;
                    padding: 20px 30px;
                    text-align: center;
                    font-size: 12px;
                    color: #9ca3af;
                    border-top: 1px solid #e5e7eb;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">
                        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAACAAAAAgACAYAAACyp9MwAADlOUlEQVR4nOzdT2yV9b74+++d0JwEbCNnwsCWZAeOOxSITMQfobgTlSMe4LgHG8il3ImAyW6HMLhlSO+gzH7tTQTP5FgSwMFR8YJuNVFKuOKkBqk5bIg3tA56B2JaIDHt5N7vs7Tbvwgs1lpdz2e9Xsmz1ue73HtqXc/zXt/v//L/ZQkAAAAAAAAAKDUBAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAAACEAAAAAAAAAAAQAACAAAAAAAAAAAIQAAAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAAAAhAAAAAAAAAAAEAAAgAAAAAAAAAACEAAAAAAAAAAAAABCAAAAAAAAAAAIAABAAAAAAAAAAAEIAAAAAAAAAAAgAAEAAAAAAAAAAAQgAAAAAAAAAAAAAIQAAAAAAAAAABAAAIAAAAAAAAAAAhAAAAAAAAAAAAAAQgAAAAAAAAAACAAAQAAAAAAAAAABCAAAAAAAAAAAIAABAAA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,others..." alt="DYLETH Logo"/>
                    </div>
                    <h1 class="header-title">DYLETH</h1>
                </div>
                <div class="content">
                    <p class="greeting">Bonjour,</p>
                    <p class="message">Nous avons reçu une demande de réinitialisation de votre mot de passe. Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe.</p>
                    <a href="{reset_url}" class="cta-button">Cliquez ici pour réinitialiser votre mot de passe</a>
                    <div class="expiry">
                        Ce lien expire dans {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
                    </div>
                    <div class="security-notice">
                        ✓ Si vous n'avez pas demandé cette réinitialisation, vous pouvez ignorer cet email en toute sécurité.
                    </div>
                </div>
                <div class="footer">
                    <p>© 2026 DYLETH. Tous droits réservés.</p>
                </div>
            </div>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(plain_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            await asyncio.to_thread(self._send_message, sender_email, recipient_email, message)
            logger.info("[email] Message transmis au serveur SMTP pour to=%s", recipient_email)
            return True
        except Exception as exc:
            logger.exception("Unable to send password reset email to %s: %s", recipient_email, exc)
            return False

    def _send_message(self, sender_email: str, recipient_email: str, message: MIMEMultipart) -> None:
        context = ssl.create_default_context()
        smtp_password_raw = settings.SMTP_PASSWORD or settings.SMTP_PASS
        smtp_password = "".join((smtp_password_raw or "").split())

        if smtp_password_raw and smtp_password_raw != smtp_password:
            logger.info("[email] SMTP password normalisé (espaces supprimés)")

        primary_secure = settings.SMTP_SECURE or settings.SMTP_PORT == 465
        attempts = [(settings.SMTP_PORT, primary_secure)]

        # Fallback automatique utile quand 587/STARTTLS timeoute sur certains réseaux.
        if settings.SMTP_PORT == 587 and not primary_secure:
            attempts.append((465, True))
        elif settings.SMTP_PORT == 465 and primary_secure:
            attempts.append((587, False))

        last_exc = None
        for index, (port, secure_mode) in enumerate(attempts, start=1):
            logger.info(
                "[email] Tentative SMTP %s/%s host=%s port=%s secure=%s timeout=%ss",
                index,
                len(attempts),
                settings.SMTP_HOST,
                port,
                secure_mode,
                settings.SMTP_TIMEOUT_SECONDS,
            )
            try:
                self._send_once(
                    sender_email=sender_email,
                    recipient_email=recipient_email,
                    message=message,
                    smtp_password=smtp_password,
                    context=context,
                    port=port,
                    secure_mode=secure_mode,
                )
                return
            except smtplib.SMTPAuthenticationError:
                logger.error(
                    "[email] Auth Gmail échouée. Vérifie SMTP_USER et App Password Gmail (16 caractères, sans espaces, compte Google avec 2FA)."
                )
                raise
            except (smtplib.SMTPServerDisconnected, TimeoutError, OSError) as exc:
                last_exc = exc
                logger.warning(
                    "[email] Tentative SMTP échouée (port=%s secure=%s): %s",
                    port,
                    secure_mode,
                    exc,
                )

        if last_exc:
            raise last_exc

    def _send_once(
        self,
        sender_email: str,
        recipient_email: str,
        message: MIMEMultipart,
        smtp_password: str,
        context: ssl.SSLContext,
        port: int,
        secure_mode: bool,
    ) -> None:
        if secure_mode:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                port,
                context=context,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            ) as server:
                if settings.SMTP_DEBUG:
                    server.set_debuglevel(1)

                logger.info("[email] Connexion SMTP_SSL établie")
                if settings.SMTP_USER and smtp_password:
                    if settings.SMTP_DEBUG:
                        # Avoid leaking AUTH exchange in terminal logs.
                        server.set_debuglevel(0)
                    logger.info("[email] Authentification SMTP en cours user=%s", settings.SMTP_USER)
                    server.login(settings.SMTP_USER, smtp_password)
                    logger.info("[email] Authentification SMTP réussie")

                response = server.sendmail(sender_email, [recipient_email], message.as_string())
                logger.info("[email] Réponse SMTP sendmail=%s (vide => accepté)", response)
            return

        with smtplib.SMTP(
            settings.SMTP_HOST,
            port,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as server:
            if settings.SMTP_DEBUG:
                server.set_debuglevel(1)

            logger.info("[email] Connexion SMTP établie")
            server.ehlo()
            logger.info("[email] EHLO initial OK")
            server.starttls(context=context)
            logger.info("[email] STARTTLS OK")
            server.ehlo()
            logger.info("[email] EHLO post-TLS OK")

            if settings.SMTP_USER and smtp_password:
                if settings.SMTP_DEBUG:
                    # Avoid leaking AUTH exchange in terminal logs.
                    server.set_debuglevel(0)
                logger.info("[email] Authentification SMTP en cours user=%s", settings.SMTP_USER)
                server.login(settings.SMTP_USER, smtp_password)
                logger.info("[email] Authentification SMTP réussie")

            response = server.sendmail(sender_email, [recipient_email], message.as_string())
            logger.info("[email] Réponse SMTP sendmail=%s (vide => accepté)", response)


email_service = EmailService()
