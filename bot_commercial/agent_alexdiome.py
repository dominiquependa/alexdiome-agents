#!/usr/bin/env python3
"""
AGENT ALEX DIOME — Bot Telegram commercial
Vente ebook "De Zéro à Importateur"
Déploiement : Railway.app
"""

import os
import json
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GUMROAD_LINK = os.environ.get("GUMROAD_LINK", "https://alexdiome.gumroad.com/l/importateur")
ADMIN_ID = os.environ.get("ADMIN_TELEGRAM_ID")
DATA_PATH = os.environ.get("DATA_PATH", "./data")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN manquant — configure-le dans Railway > Variables")

# ============================================================
# PERSISTENCE JSON (data/ — monter en volume Railway pour persister)
# ============================================================

Path(DATA_PATH).mkdir(parents=True, exist_ok=True)

def _load(filename, default):
    fp = os.path.join(DATA_PATH, filename)
    if not os.path.exists(fp):
        return default
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}
    except Exception as e:
        logger.error(f"Erreur lecture {filename}: {e}")
        return default

def _save(filename, data):
    fp = os.path.join(DATA_PATH, filename)
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erreur écriture {filename}: {e}")

prospects = _load("prospects.json", {})
clients = _load("clients.json", {})

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

    if user_id not in prospects and user_id not in clients:
        prospects[user_id] = {
            "name": user.first_name,
            "username": user.username,
            "stage": "nouveau",
            "messages": 0
        }
        _save("prospects.json", prospects)
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"🆕 Nouveau prospect : {user.first_name} (@{user.username})"
                )
            except Exception as e:
                logger.error(f"Notif admin échouée: {e}")

    await update.message.reply_text(
        MSG_BIENVENUE,
        parse_mode="Markdown",
        reply_markup=keyboard_principal()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if user_id in prospects:
        prospects[user_id]["messages"] += 1
        stage = prospects[user_id]["messages"]
        _save("prospects.json", prospects)

        if stage == 3:
            await update.message.reply_text(MSG_RELANCE_1, parse_mode="Markdown")
            return
        elif stage == 6:
            await update.message.reply_text(MSG_RELANCE_2, parse_mode="Markdown")
            return

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
        clients[user_id] = {"name": update.effective_user.first_name, "purchased": True}
        if user_id in prospects:
            del prospects[user_id]
        _save("clients.json", clients)
        _save("prospects.json", prospects)
        await update.message.reply_text(MSG_APRES_ACHAT, parse_mode="Markdown")
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"💰 VENTE ! {update.effective_user.first_name} a acheté le guide !"
                )
            except Exception as e:
                logger.error(f"Notif vente échouée: {e}")
    else:
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
    for user_id in list(prospects.keys()):
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Message envoyé à {count} prospects.")

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exporte la base prospects + clients en JSON — /export"""
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    payload = {"prospects": prospects, "clients": clients}
    txt = json.dumps(payload, ensure_ascii=False, indent=2)
    # Telegram limite à 4096 chars par message
    if len(txt) > 3500:
        await update.message.reply_text(
            f"📦 Base : {len(prospects)} prospects · {len(clients)} clients\n"
            f"(Trop volumineuse pour Telegram — consulte directement /data sur Railway)"
        )
    else:
        await update.message.reply_text(f"```\n{txt}\n```", parse_mode="Markdown")

# ============================================================
# MAIN
# ============================================================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("export", export_data))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Agent Alex Diome (commercial) démarré...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
