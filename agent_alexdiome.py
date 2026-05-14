#!/usr/bin/env python3
"""
AGENT ALEX DIOME — Bot Telegram/WhatsApp
Vente ebook "De Zéro à Importateur" + Suivi clients
Déploiement : Railway.app (comme ton bot Alexia)
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from bot_persistence import (
    load_named_int_dict,
    persistence_dir,
    save_named_int_dict,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ============================================================
# CONFIGURATION
# ============================================================

# Per-service on Railway you can set TELEGRAM_TOKEN only, or use a named var on a shared template:
TOKEN = os.environ.get("TELEGRAM_TOKEN_ALEXDIOME") or os.environ.get("TELEGRAM_TOKEN")
GUMROAD_LINK = os.environ.get("GUMROAD_LINK", "https://alexdiome.gumroad.com/l/importateur")
ADMIN_ID = os.environ.get("ADMIN_TELEGRAM_ID")  # Ton ID Telegram pour recevoir les notifs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# ÉTAT PERSISTANT (JSON sur volume Railway ou ./data)
# ============================================================

_FILE_PROSPECTS = "alexdiome_commercial_prospects.json"
_FILE_CLIENTS = "alexdiome_commercial_clients.json"

# {user_id: {"name": str, "stage": str, "messages": int}}
prospects: dict = {}
# {user_id: {"name": str, "purchased": True}}
clients: dict = {}


def _load_state():
    global prospects, clients
    prospects.clear()
    clients.clear()
    prospects.update(load_named_int_dict(_FILE_PROSPECTS))
    clients.update(load_named_int_dict(_FILE_CLIENTS))


def _persist_prospects():
    save_named_int_dict(_FILE_PROSPECTS, prospects)


def _persist_clients():
    save_named_int_dict(_FILE_CLIENTS, clients)

# ============================================================
# MESSAGES ALEX DIOME
# ============================================================

MSG_BIENVENUE = """
👋 Bienvenue ! Je suis Alex Diome.

Depuis 5 ans, j'importe depuis la Chine et je vends en Afrique et en Europe.

Mon guide *"De Zéro à Importateur"* te donne toutes mes méthodes :
✅ Trouver les bons produits
✅ Négocier avec les fournisseurs
✅ Gérer la logistique
✅ Vendre en Afrique et à la diaspora

👇 Que veux-tu faire ?
"""

MSG_GUIDE_INFO = """
📦 *De Zéro à Importateur*
_Le Guide Complet Chine-Afrique_

*Ce que tu vas apprendre :*
• Les 3 plateformes chinoises incontournables
• 50 produits gagnants avec leurs marges
• Les 7 règles d'or pour ne pas se faire arnaquer
• Calcul exact de ta marge avant chaque commande
• Comment vendre en Afrique ET à la diaspora
• Modèles de messages fournisseurs prêts à l'emploi

*Prix de lancement :* 12€ / 8 000 FCFA
_(limité aux 100 premiers acheteurs)_

👉 Prêt à commander ?
"""

MSG_ACHETER = """
💳 *Pour obtenir ton guide maintenant :*

🌍 *Diaspora Europe (PayPal/Carte) :*
{}

🌱 *Afrique (MTN/Orange Money) :*
Envoie le paiement au numéro WhatsApp et envoie-moi la capture de confirmation.

⚡ Livraison immédiate après paiement !
""".format(GUMROAD_LINK)

MSG_FAQ_1 = """
❓ *C'est pour qui ce guide ?*

✅ Tu veux démarrer un business import avec peu de capital
✅ Tu es en Europe et tu veux investir en Afrique
✅ Tu vends déjà mais tu veux augmenter tes marges
✅ Tu cherches une activité sérieuse et rentable

Quel que soit ton niveau, le guide part de zéro.
"""

MSG_FAQ_2 = """
❓ *Combien faut-il pour commencer ?*

Avec *50 000 FCFA* tu peux passer ta première commande.

Exemple réel :
• Capital investi : 75 000 FCFA
• Vendu en 3 semaines sur WhatsApp
• Chiffre d'affaires : 420 000 FCFA
• Bénéfice net : 345 000 FCFA

Le guide t'explique exactement comment reproduire ça.
"""

MSG_FAQ_3 = """
❓ *Est-ce que ça marche vraiment ?*

Oui. La Chine exporte pour 250 milliards de dollars vers l'Afrique chaque année.

La majorité des produits autour de toi viennent de Chine. La question c'est : est-ce que tu achètes via des intermédiaires ou directement à la source ?

Ce guide te montre comment aller à la source.
"""

MSG_APRES_ACHAT = """
🎉 *Félicitations et bienvenue dans la famille !*

Ton guide est en route sur ton email.

*3 premières étapes à faire maintenant :*
1. Crée ton compte Alibaba gratuit
2. Cherche ton premier produit
3. Contacte 3 fournisseurs avec le modèle du guide

Des questions ? Réponds ici, je suis là.

À ton succès 🚀
_Alex Diome_
"""

MSG_RELANCE_1 = """
👋 Hé, tu es encore là ?

Je voulais juste te dire que le prix de lancement à 8 000 FCFA ne dure pas.

Les premières places partent vite.

Tu veux que je te réponde à une question avant que tu te décides ?
"""

MSG_RELANCE_2 = """
📊 Petit rappel des chiffres :

• Capital de départ minimum : 50 000 FCFA
• Marge typique par produit : 300% à 500%
• Délai pour première vente : 30 à 60 jours

Le seul risque c'est de ne pas commencer.

👉 {}
""".format(GUMROAD_LINK)

# ============================================================
# KEYBOARDS
# ============================================================

def keyboard_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Voir le guide", callback_data="guide_info")],
        [InlineKeyboardButton("💳 Acheter maintenant", callback_data="acheter")],
        [InlineKeyboardButton("❓ Questions fréquentes", callback_data="faq")],
        [InlineKeyboardButton("📞 Parler à Alex", callback_data="contact")],
    ])

def keyboard_faq():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("C'est pour qui ?", callback_data="faq_1")],
        [InlineKeyboardButton("Combien de capital ?", callback_data="faq_2")],
        [InlineKeyboardButton("Est-ce que ça marche ?", callback_data="faq_3")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="retour")],
    ])

def keyboard_acheter():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Acheter (PayPal/Carte)", url=GUMROAD_LINK)],
        [InlineKeyboardButton("📱 Payer MTN/Orange Money", callback_data="mobile_money")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="retour")],
    ])

# ============================================================
# HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Enregistre le prospect
    if user_id not in prospects and user_id not in clients:
        prospects[user_id] = {
            "name": user.first_name,
            "stage": "nouveau",
            "messages": 0
        }
        _persist_prospects()
        # Notifie l'admin
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🆕 Nouveau prospect : {user.first_name} (@{user.username})"
            )

    await update.message.reply_text(
        MSG_BIENVENUE,
        parse_mode="Markdown",
        reply_markup=keyboard_principal()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    # Incrémente le compteur de messages
    if user_id in prospects:
        prospects[user_id]["messages"] += 1
        stage = prospects[user_id]["messages"]
        _persist_prospects()

        # Logique de relance progressive
        if stage == 3:
            await update.message.reply_text(MSG_RELANCE_1, parse_mode="Markdown")
            return
        elif stage == 6:
            await update.message.reply_text(MSG_RELANCE_2, parse_mode="Markdown")
            return

    # Détection mots-clés
    if any(word in text for word in ["prix", "combien", "coût", "tarif"]):
        await update.message.reply_text(MSG_GUIDE_INFO, parse_mode="Markdown",
                                        reply_markup=keyboard_acheter())
    elif any(word in text for word in ["acheter", "commander", "payer", "achete"]):
        await update.message.reply_text(MSG_ACHETER, parse_mode="Markdown",
                                        reply_markup=keyboard_acheter())
    elif any(word in text for word in ["chine", "alibaba", "importer", "import"]):
        await update.message.reply_text(MSG_FAQ_3, parse_mode="Markdown",
                                        reply_markup=keyboard_principal())
    elif any(word in text for word in ["capital", "argent", "budget", "fcfa"]):
        await update.message.reply_text(MSG_FAQ_2, parse_mode="Markdown",
                                        reply_markup=keyboard_principal())
    elif any(word in text for word in ["merci", "reçu", "recu", "payé", "paye", "acheté"]):
        # Client qui a payé
        clients[user_id] = {"name": update.effective_user.first_name, "purchased": True}
        if user_id in prospects:
            del prospects[user_id]
        _persist_prospects()
        _persist_clients()
        await update.message.reply_text(MSG_APRES_ACHAT, parse_mode="Markdown")
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"💰 VENTE ! {update.effective_user.first_name} a acheté le guide !"
            )
    else:
        # Réponse générique + menu
        await update.message.reply_text(
            "Je suis là pour t'aider ! Voici ce que je peux faire pour toi 👇",
            reply_markup=keyboard_principal()
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "guide_info":
        await query.message.reply_text(MSG_GUIDE_INFO, parse_mode="Markdown",
                                       reply_markup=keyboard_acheter())
    elif data == "acheter":
        await query.message.reply_text(MSG_ACHETER, parse_mode="Markdown",
                                       reply_markup=keyboard_acheter())
    elif data == "faq":
        await query.message.reply_text(
            "❓ *Questions fréquentes — choisis ta question :*",
            parse_mode="Markdown",
            reply_markup=keyboard_faq()
        )
    elif data == "faq_1":
        await query.message.reply_text(MSG_FAQ_1, parse_mode="Markdown",
                                       reply_markup=keyboard_acheter())
    elif data == "faq_2":
        await query.message.reply_text(MSG_FAQ_2, parse_mode="Markdown",
                                       reply_markup=keyboard_acheter())
    elif data == "faq_3":
        await query.message.reply_text(MSG_FAQ_3, parse_mode="Markdown",
                                       reply_markup=keyboard_acheter())
    elif data == "mobile_money":
        await query.message.reply_text(
            "📱 *Paiement MTN/Orange Money :*\n\n"
            "Envoie *8 000 FCFA* au numéro indiqué par Alex.\n\n"
            "Ensuite envoie-moi ici la *capture d'écran* de la confirmation.\n"
            "Le guide te sera envoyé dans les 30 minutes.",
            parse_mode="Markdown"
        )
    elif data == "contact":
        await query.message.reply_text(
            "📞 *Parler directement à Alex :*\n\n"
            "Pose ta question ici et Alex te répond personnellement.\n\n"
            "Email : contact@alexdiome.com",
            parse_mode="Markdown"
        )
    elif data == "retour":
        await query.message.reply_text(
            MSG_BIENVENUE,
            parse_mode="Markdown",
            reply_markup=keyboard_principal()
        )

# ============================================================
# COMMANDES ADMIN
# ============================================================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    msg = (
        f"📊 *Stats Alex Diome Bot*\n\n"
        f"👥 Prospects actifs : {len(prospects)}\n"
        f"💰 Clients acheteurs : {len(clients)}\n"
        f"📈 Total contacts : {len(prospects) + len(clients)}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envoie un message à tous les prospects — /broadcast Ton message ici"""
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast Ton message")
        return
    message = " ".join(context.args)
    count = 0
    for user_id in prospects:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Message envoyé à {count} prospects.")

# ============================================================
# MAIN
# ============================================================

def main():
    if not TOKEN:
        raise SystemExit(
            "Missing token: set TELEGRAM_TOKEN or TELEGRAM_TOKEN_ALEXDIOME for this service."
        )
    _load_state()
    logger.info("Persistence dir: %s", persistence_dir())

    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Agent Alex Diome démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()
