#!/usr/bin/env python3
"""
AGENT SUIVI POST-ACHAT + UPSELL — Alex Diome
Séquence automatique après achat de l'ebook
Déploiement : Railway.app
"""

import os
import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from bot_persistence import load_named_int_dict, persistence_dir, save_named_int_dict
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    JobQueue,
    MessageHandler,
    filters,
)

# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.environ.get("TELEGRAM_TOKEN_SUIVI_UPSELL") or os.environ.get("TELEGRAM_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_TELEGRAM_ID")
GUMROAD_LINK = os.environ.get("GUMROAD_LINK", "https://alexdiome.gumroad.com/l/importateur")
UPSELL_LINK = os.environ.get("UPSELL_LINK", "https://alexdiome.gumroad.com/l/coaching")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# BASE DE DONNÉES CLIENTS (persistée en JSON)
# ============================================================

_FILE_CLIENTS = "alexdiome_suivi_clients.json"

# Structure : {user_id: {"name", "purchase_date", "day_sequence", "upsell_offered", ...}}
clients_db: dict = {}


def _load_clients_db():
    global clients_db
    clients_db.clear()
    clients_db.update(load_named_int_dict(_FILE_CLIENTS))


def _persist_clients_db():
    save_named_int_dict(_FILE_CLIENTS, clients_db)

# ============================================================
# SÉQUENCE POST-ACHAT — 7 JOURS
# ============================================================

SEQUENCE = {
    1: {
        "titre": "Jour 1 — Bienvenue dans le voyage",
        "message": """
🎉 *Jour 1 — Tu as fait le bon choix.*

Félicitations pour ton guide !

Aujourd'hui une seule chose à faire :

👉 *Crée ton compte Alibaba gratuit*
→ alibaba.com → Sign Up

Prends 10 minutes. C'est ta porte d'entrée vers les fournisseurs chinois.

Demain je t'envoie comment trouver ton premier produit gagnant.

_Alex Diome_
"""
    },
    2: {
        "titre": "Jour 2 — Ton premier produit",
        "message": """
📦 *Jour 2 — Trouver ton produit gagnant*

Sur Alibaba, tape dans la recherche :
→ *"cosmetics wholesale"*
→ *"phone accessories wholesale"*

*Ce que tu cherches :*
✅ Prix unitaire moins de 2$ pour débuter
✅ Minimum Order Quantity (MOQ) 50 pièces max
✅ Fournisseur avec badge "Verified Supplier"

Note 3 produits qui t'intéressent.

Demain je t'explique comment contacter les fournisseurs.

_Alex Diome_
"""
    },
    3: {
        "titre": "Jour 3 — Contacter les fournisseurs",
        "message": """
📧 *Jour 3 — Envoie ton premier message fournisseur*

Prends le modèle de message du chapitre 4 de ton guide.

Envoie-le à *5 fournisseurs différents* pour le même produit.

*Règle d'or :* Ne contacte jamais un seul fournisseur. La concurrence joue pour toi.

Dans 24-48h tu auras des réponses avec les prix.

C'est là que la négociation commence.

_Alex Diome_
"""
    },
    4: {
        "titre": "Jour 4 — Calculer ta marge",
        "message": """
🧮 *Jour 4 — Calcule ta marge AVANT de commander*

Tu as les prix des fournisseurs ?

Utilise cette formule du guide :

*Prix de revient réel =*
Prix produit + Agent (8%) + Fret + Douane + Transitaire

*Règle absolue :*
Ne commande jamais en dessous de 3x ton prix de revient.

Si la marge n'est pas là → change de produit. Simple.

_Alex Diome_
"""
    },
    5: {
        "titre": "Jour 5 — Prépare ta vente",
        "message": """
📱 *Jour 5 — Prépare ton WhatsApp Business*

Avant même de commander, prépare ta vitrine :

1. Télécharge *WhatsApp Business*
2. Photo de profil professionnelle
3. Description : ce que tu vends
4. Catalogue : ajoute les photos produits du fournisseur
5. Message de bienvenue automatique

Tes premiers clients arrivent via WhatsApp. Sois prêt.

_Alex Diome_
"""
    },
    6: {
        "titre": "Jour 6 — Passe ta première commande",
        "message": """
🚀 *Jour 6 — Le moment de passer à l'action*

Tu as :
✅ Ton compte Alibaba
✅ Ton produit sélectionné
✅ Ta marge calculée
✅ Ton WhatsApp Business prêt

*Il reste une seule chose : commander.*

Commence petit. 20 à 50 pièces maximum pour le premier ordre.

Tu valides la qualité. Tu vends. Tu recommandes en plus grande quantité.

C'est le cycle qui construit ton business.

_Alex Diome_
"""
    },
    7: {
        "titre": "Jour 7 — Bilan et prochaine étape",
        "message": """
🏆 *Jour 7 — Tu es prêt.*

En 7 jours tu as :
→ Ton compte Alibaba créé
→ Ton produit identifié
→ Tes fournisseurs contactés
→ Ta marge calculée
→ Ton WhatsApp Business prêt

La majorité des gens qui achètent des guides n'agissent jamais.

*Toi tu as agi.*

---

🎯 *Prochaine étape : aller plus loin*

Beaucoup de mes clients me demandent un accompagnement personnalisé pour :
• Choisir le bon produit selon leur budget
• Négocier directement avec mes fournisseurs
• Construire leur réseau de revendeurs

Si tu veux aller plus vite avec mon aide directe, réponds *"COACHING"* ici.

_Alex Diome_
"""
    }
}

# ============================================================
# MESSAGES UPSELL
# ============================================================

MSG_UPSELL = """
🎯 *Coaching Personnalisé — Alex Diome*

Tu as le guide. Maintenant passe à la vitesse supérieure.

*Ce que tu obtiens avec le coaching :*
✅ 3 sessions vidéo avec Alex (1h chacune)
✅ Sélection personnalisée de tes 3 produits gagnants
✅ Introduction directe à mes fournisseurs fiables
✅ Suivi WhatsApp pendant 30 jours
✅ Accès au groupe privé importateurs

*Pour qui :*
→ Tu veux aller plus vite
→ Tu veux éviter les erreurs coûteuses
→ Tu veux mes contacts directs en Chine

*Prix :* 150€ / 100 000 FCFA

Places limitées à 10 par mois.

👉 Réserver ma place : {}
""".format(UPSELL_LINK)

MSG_TEMOIGNAGE_REQUEST = """
⭐ *Une dernière chose...*

Tu utilises le guide depuis quelques jours maintenant.

Est-ce que tu peux me dire en 2-3 phrases comment ça se passe pour toi ?

Ton retour m'aide à améliorer le guide et aide d'autres personnes à se décider.

Merci 🙏
_Alex Diome_
"""

MSG_REFERRAL = """
👥 *Programme Partenaire Alex Diome*

Tu connais quelqu'un qui voudrait importer depuis la Chine ?

*Comment ça marche :*
→ Tu partages ton lien personnel
→ Quelqu'un achète via ton lien
→ Tu reçois *30% de commission* — soit 2 400 FCFA par vente

Pour obtenir ton lien affilié personnel, réponds *"AFFILIÉ"* ici.

_Alex Diome_
"""

# ============================================================
# KEYBOARDS
# ============================================================

def keyboard_suivi(jour):
    buttons = [[InlineKeyboardButton("✅ C'est fait !", callback_data=f"done_{jour}")]]
    if jour >= 7:
        buttons.append([InlineKeyboardButton("🎯 En savoir plus sur le coaching", callback_data="upsell")])
    buttons.append([InlineKeyboardButton("❓ J'ai une question", callback_data="question")])
    return InlineKeyboardMarkup(buttons)

def keyboard_upsell():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Je veux le coaching", url=UPSELL_LINK)],
        [InlineKeyboardButton("👥 Programme affilié", callback_data="referral")],
        [InlineKeyboardButton("Pas maintenant", callback_data="plus_tard")],
    ])

# ============================================================
# HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enregistre un nouveau client et démarre la séquence"""
    user = update.effective_user
    user_id = user.id

    clients_db[user_id] = {
        "name": user.first_name,
        "purchase_date": datetime.now().isoformat(),
        "day_sequence": 1,
        "upsell_offered": False,
        "testimonial_requested": False
    }
    _persist_clients_db()

    # Message de bienvenue jour 1
    msg = SEQUENCE[1]["message"]
    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=keyboard_suivi(1)
    )

    # Notifie admin
    if ADMIN_ID:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 Nouveau client séquence : {user.first_name} (@{user.username})"
        )

async def envoyer_jour(context: ContextTypes.DEFAULT_TYPE):
    """Job quotidien — envoie le message du jour à chaque client"""
    for user_id, data in list(clients_db.items()):
        jour = data.get("day_sequence", 1)

        if jour > 7:
            # Séquence terminée — propose upsell si pas encore fait
            if not data.get("upsell_offered"):
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=MSG_UPSELL,
                        parse_mode="Markdown",
                        reply_markup=keyboard_upsell()
                    )
                    clients_db[user_id]["upsell_offered"] = True
                    _persist_clients_db()
                except Exception as e:
                    logger.error(f"Erreur upsell {user_id}: {e}")
            continue

        try:
            msg = SEQUENCE[jour]["message"]
            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                parse_mode="Markdown",
                reply_markup=keyboard_suivi(jour)
            )
            # Avance au jour suivant
            clients_db[user_id]["day_sequence"] += 1

            # Jour 5 → demande témoignage
            if jour == 5 and not data.get("testimonial_requested"):
                await asyncio.sleep(3)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=MSG_TEMOIGNAGE_REQUEST,
                    parse_mode="Markdown"
                )
                clients_db[user_id]["testimonial_requested"] = True

            # Jour 7 → propose programme affilié
            if jour == 7:
                await asyncio.sleep(5)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=MSG_REFERRAL,
                    parse_mode="Markdown"
                )
            _persist_clients_db()

        except Exception as e:
            logger.error(f"Erreur envoi jour {jour} à {user_id}: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("done_"):
        jour = int(data.split("_")[1])
        await query.message.reply_text(
            f"💪 Excellent ! Tu avances bien.\n\nLe message de demain arrive dans 24h.",
            parse_mode="Markdown"
        )

    elif data == "upsell":
        await query.message.reply_text(
            MSG_UPSELL,
            parse_mode="Markdown",
            reply_markup=keyboard_upsell()
        )
        if user_id in clients_db:
            clients_db[user_id]["upsell_offered"] = True
            _persist_clients_db()

    elif data == "referral":
        await query.message.reply_text(
            MSG_REFERRAL,
            parse_mode="Markdown"
        )

    elif data == "question":
        await query.message.reply_text(
            "Pose ta question ici, Alex te répond personnellement 👇",
            parse_mode="Markdown"
        )

    elif data == "plus_tard":
        await query.message.reply_text(
            "Pas de souci ! Je suis là quand tu es prêt. 🤝",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if "coaching" in text:
        await update.message.reply_text(
            MSG_UPSELL,
            parse_mode="Markdown",
            reply_markup=keyboard_upsell()
        )
    elif "affili" in text:
        await update.message.reply_text(
            "Pour obtenir ton lien affilié personnel, envoie ton email à contact@alexdiome.com\n\n"
            "Tu recevras ton lien et les instructions dans les 24h. 👍",
            parse_mode="Markdown"
        )
    else:
        # Transfert à l'admin pour réponse personnelle
        if ADMIN_ID:
            client_name = clients_db.get(user_id, {}).get("name", "Inconnu")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"💬 Message de {client_name} (ID: {user_id}) :\n\n{update.message.text}\n\n"
                     f"Réponds via /reply {user_id} [ton message]"
            )
        await update.message.reply_text(
            "Message reçu ! Alex te répond dans les plus brefs délais. ⚡",
            parse_mode="Markdown"
        )

async def reply_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin répond à un client — /reply USER_ID Message"""
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reply USER_ID Message")
        return
    target_id = context.args[0]
    message = " ".join(context.args[1:])
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"💬 *Alex Diome :*\n\n{message}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Message envoyé.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    total = len(clients_db)
    upsell_offered = sum(1 for c in clients_db.values() if c.get("upsell_offered"))
    completed = sum(1 for c in clients_db.values() if c.get("day_sequence", 1) > 7)
    msg = (
        f"📊 *Stats Séquence Post-Achat*\n\n"
        f"👥 Clients totaux : {total}\n"
        f"✅ Séquence complétée : {completed}\n"
        f"🎯 Upsell proposé : {upsell_offered}\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ============================================================
# MAIN
# ============================================================

def _scheduler_timezone() -> ZoneInfo:
    """IANA zone for daily job (e.g. Europe/Paris). Falls back to UTC."""
    name = os.environ.get("SCHEDULER_TIMEZONE") or os.environ.get("TZ") or "UTC"
    try:
        return ZoneInfo(name)
    except Exception:
        logger.warning("Invalid SCHEDULER_TIMEZONE/TZ=%r, using UTC", name)
        return ZoneInfo("UTC")


def main():
    if not TOKEN:
        raise SystemExit(
            "Missing token: set TELEGRAM_TOKEN or TELEGRAM_TOKEN_SUIVI_UPSELL for this service."
        )
    _load_clients_db()
    tz = _scheduler_timezone()
    logger.info("Persistence dir: %s", persistence_dir())
    logger.info("Scheduler timezone: %s", tz)

    app = (
        Application.builder()
        .token(TOKEN)
        .job_queue(JobQueue(timezone=tz))
        .build()
    )

    # Job quotidien à 9h00 (heure du fuseau SCHEDULER_TIMEZONE / TZ)
    app.job_queue.run_daily(
        envoyer_jour,
        time=datetime.strptime("09:00", "%H:%M").time(),
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reply", reply_client))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Agent Suivi Post-Achat démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()
