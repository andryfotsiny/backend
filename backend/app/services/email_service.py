import asyncio
import logging
import smtplib
import ssl
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)
LOGO_CID = "dyleth-logo"
LOGO_PATH = Path(__file__).resolve().parents[2] / "data" / "favicon.png"


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
            <meta name="color-scheme" content="light dark">
            <meta name="supported-color-schemes" content="light dark">
            <title>Réinitialisation du mot de passe · DYLETH</title>
            <style>
                :root {{ color-scheme: light dark; supported-color-schemes: light dark; }}
                html, body {{ margin:0 !important; padding:0 !important; height:100% !important; width:100% !important; }}
                a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; }}
                @media (prefers-color-scheme: dark) {{
                    .bg {{ background: #0b0c0e !important; }}
                    .card {{ background: #111827 !important; color: #e5e7eb !important; }}
                    .muted {{ color: #9ca3af !important; }}
                    .btn {{ background: #2563eb !important; }}
                    .bordered {{ border-color: #1f2937 !important; }}
                }}
            </style>
        </head>
        <body class="bg" style="background:#f3f4f6; margin:0; padding:0;">
            <!-- Preheader (affiché dans l'aperçu des boîtes mail) -->
            <div style="display:none; max-height:0; overflow:hidden; opacity:0; mso-hide:all;">
                Réinitialisez votre mot de passe pour accéder à votre compte DYLETH. Ce lien expire dans {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
            </div>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f3f4f6;">
                <tr>
                    <td align="center" style="padding:24px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" class="card bordered" style="width:600px; max-width:600px; background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden;">
                            <tr>
                                <td align="center" style="padding:36px 24px 0 24px;">
                                    <img src="cid:{LOGO_CID}" width="72" height="72" alt="Logo DYLETH" style="display:block; width:72px; height:72px; margin:0 auto 12px auto; border:0; outline:none; text-decoration:none;">
                                    <h1 style="margin:0; font-family:Segoe UI, Arial, sans-serif; font-size:24px; line-height:32px; font-weight:700; color:#111827;">DYLETH</h1>
                                </td>
                            </tr>
                            <tr>
                                <td align="left" style="padding:32px 32px 0 32px; font-family:Segoe UI, Arial, sans-serif; color:#374151; font-size:16px; line-height:24px;">
                                    Bonjour,
                                </td>
                            </tr>
                            <tr>
                                <td align="left" style="padding:12px 32px 0 32px; font-family:Segoe UI, Arial, sans-serif; color:#6b7280; font-size:14px; line-height:22px;">
                                    Nous avons reçu une demande de réinitialisation de votre mot de passe. Cliquez sur le bouton ci‑dessous pour choisir un nouveau mot de passe.
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="padding:28px 32px 8px 32px;">
                                    <!--[if mso]>
                                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="{reset_url}" style="height:48px;v-text-anchor:middle;width:460px;" arcsize="8%" strokecolor="none" fillcolor="#111827">
                                        <w:anchorlock/>
                                        <center style="color:#ffffff; font-family:Segoe UI, Arial, sans-serif; font-size:16px; font-weight:700;">
                                            Cliquez ici pour réinitialiser votre mot de passe
                                        </center>
                                    </v:roundrect>
                                    <![endif]-->
                                    <!--[if !mso]><!-- -->
                                    <a href="{reset_url}" class="btn" style="display:inline-block; background:#111827; color:#ffffff; text-decoration:none; font-family:Segoe UI, Arial, sans-serif; font-weight:700; font-size:16px; line-height:24px; padding:14px 24px; border-radius:8px;">
                                        Cliquez ici pour réinitialiser votre mot de passe
                                    </a>
                                    <!--<![endif]-->
                                </td>
                            </tr>   
                            <tr>
                                <td align="left" style="padding:16px 32px 0 32px; font-family:Segoe UI, Arial, sans-serif; font-size:12px; line-height:18px; color:#6b7280; border-top:1px solid #e5e7eb;" class="bordered">
                                    Ce lien expire dans {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
                                </td>
                            </tr>
                            <tr>
                                <td align="left" style="padding:16px 32px 32px 32px;">
                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background:#f9fafb; border-left:4px solid #10b981; border-radius:6px;">
                                        <tr>
                                            <td style="padding:12px 14px; font-family:Segoe UI, Arial, sans-serif; font-size:12px; line-height:18px; color:#6b7280;">
                                                ✓ Si vous n'avez pas demandé cette réinitialisation, vous pouvez ignorer cet email en toute sécurité.
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="padding:0 24px 24px 24px;">
                                    <p class="muted" style="margin:0; font-family:Segoe UI, Arial, sans-serif; font-size:12px; line-height:18px; color:#9ca3af;">
                                        © 2026 DYLETH. Tous droits réservés.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        message = MIMEMultipart("related")
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = recipient_email
        message["Subject"] = subject

        alternative_part = MIMEMultipart("alternative")
        alternative_part.attach(MIMEText(plain_body, "plain", "utf-8"))
        alternative_part.attach(MIMEText(html_body, "html", "utf-8"))
        message.attach(alternative_part)

        if LOGO_PATH.exists():
            with LOGO_PATH.open("rb") as logo_file:
                logo_part = MIMEImage(logo_file.read())
            logo_part.add_header("Content-ID", f"<{LOGO_CID}>")
            logo_part.add_header("Content-Disposition", "inline", filename=LOGO_PATH.name)
            message.attach(logo_part)
        else:
            logger.warning("[email] Logo introuvable: %s", LOGO_PATH)

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
