import os
import time
import threading
import math
import itertools
import requests
from bs4 import BeautifulSoup
from flask import Flask
from fbchat import Client
from fbchat.models import *

# ================= KONFIGURACJA FB (MUSISZ UZUPEŁNIĆ) =================
# 1. Wpisz ciasteczka z fejk konta:
C_USER = "61577436214659"
XS = "17%3AUFJYxNsG8KOTLQ%3A2%3A1774541320%3A-1%3A-1"    

# 2. Wpisz ID docelowe (na start wpisz swoje własne ID z FB, żeby bot pisał do Ciebie na priv)
# Swoje ID wyciągniesz np. ze strony findmyfbid.in
THREAD_ID = "1448789500057277"
THREAD_TYPE = ThreadType.USER # Zmienimy na ThreadType.GROUP jak dodasz go na grupe
# ======================================================================

# ================= KONFIGURACJA TIBIA =================
SWIAT = "Antica"
LISTA_GRACZY = ["Oakizy", "Lightning Erteria", "Siutok", "Lamus Mpa"]
MIASTA = ["Thais", "Venore", "Carlin", "Edron", "Darashia", "Ankrahmun", "Yalahar"]

HEADERS = {'User-Agent': 'Mozilla/5.0'}
stan_graczy = {n.lower(): {'online': False, 'lvl': 0} for n in LISTA_GRACZY}

# ================= ANTY-SLEEP (FLASK) =================
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Szpieg na Messengera zyje i ma sie dobrze! 24/7"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ================= LOGIKA TIBII =================
def get_char_info(nick):
    try:
        r = requests.get(f"https://api.tibiadata.com/v4/character/{nick}", headers=HEADERS, timeout=10).json()
        c = r['character']['character']
        lvl, voc = c['level'], c['vocation']
        
        if "Monk" in voc: hp, mp, cap = (lvl*10+185), (lvl*10+35), (lvl*20+390)
        elif "Knight" in voc: hp, mp, cap = (lvl*15+185), (lvl*5+35), (lvl*25+390)
        elif "Paladin" in voc: hp, mp, cap = (lvl*10+185), (lvl*15+35), (lvl*20+390)
        else: hp, mp, cap = (lvl*5+185), (lvl*30+35), (lvl*10+390)
        
        return {
            'nick': nick, 'lvl': lvl, 'voc': voc,
            'min': math.ceil(lvl*2/3), 'max': math.floor(lvl*3/2),
            'score': round((lvl*3)+((hp+mp+cap)/25), 1),
            'pacc': "Premium" in str(c.get('account_status', ''))
        }
    except: return None

# ================= SZPIEG (Wysyła powiadomienia) =================
bot_client = None

def szpieg_monitorujacy():
    global stan_graczy, bot_client
    pierwszy_przebieg = True
    print("🕵️‍♂️ Szpieg taktyczny gotowy...")
    while True:
        if bot_client and bot_client.isLoggedIn():
            try:
                r = requests.get(f"https://api.tibiadata.com/v4/world/{SWIAT}", headers=HEADERS, timeout=15)
                if r.status_code == 200:
                    dane = r.json().get('world', {}).get('online_players', [])
                    obecnie_on = {p['name'].lower(): p['level'] for p in dane if p['name'].lower() in stan_graczy}
                    
                    for nick_l in stan_graczy:
                        teraz_on = nick_l in obecnie_on
                        lvl_teraz = obecnie_on.get(nick_l, 0)
                        poprzedni = stan_graczy[nick_l]
                        name = next(n for n in LISTA_GRACZY if n.lower() == nick_l)
                        
                        if not pierwszy_przebieg:
                            # LOGOWANIE I WYLOGOWANIE (Zostawione do testów!)
                            if teraz_on and not poprzedni['online']:
                                bot_client.send(Message(text=f"🟢 LOGOWANIE: {name} (Lvl: {lvl_teraz}) wszedł do gry!"), thread_id=THREAD_ID, thread_type=THREAD_TYPE)
                            elif not teraz_on and poprzedni['online']:
                                bot_client.send(Message(text=f"🔴 WYLOGOWANIE: {name} opuścił grę."), thread_id=THREAD_ID, thread_type=THREAD_TYPE)
                            
                            if teraz_on and poprzedni['lvl'] > 0 and lvl_teraz > poprzedni['lvl']:
                                bot_client.send(Message(text=f"🎊 LEVEL UP: {name} awansował na level {lvl_teraz}!"), thread_id=THREAD_ID, thread_type=THREAD_TYPE)

                        stan_graczy[nick_l]['online'] = teraz_on
                        if lvl_teraz > 0: stan_graczy[nick_l]['lvl'] = lvl_teraz
                    
                    pierwszy_przebieg = False
            except: pass
        time.sleep(60)

# ================= BOT MESSENGERA (Odbiera komendy) =================
class TibiaBot(Client):
    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        # Ignoruj własne wiadomości bota
        if author_id == self.uid:
            return
            
        m = message_object.text.lower() if message_object.text else ""

        if m == '!staty':
            self.send(Message(text="Skanowanie potęgi ekipy... ⏳"), thread_id=thread_id, thread_type=thread_type)
            stats = [s for s in [get_char_info(n) for n in LISTA_GRACZY] if s]
            stats.sort(key=lambda x: x['lvl'], reverse=True)
            
            if stats:
                res = "📊 STATYSTYKI I SHARE RANGE\n--------------------------\n\n"
                for p in stats:
                    res += f"👤 {p['nick']} (Lvl: {p['lvl']})\n"
                    res += f"   • Prof: {p['voc']}\n"
                    res += f"   • Share: {p['min']} - {p['max']}\n"
                    res += f"   • CC Score: {p['score']}\n\n"
                
                res += "🤝 GRUPY PARTY:\n"
                f = False
                for r in range(4, 1, -1):
                    for combo in itertools.combinations(stats, r):
                        lvls = [c['lvl'] for c in combo]
                        if min(lvls) >= math.ceil(max(lvls) * 2 / 3):
                            f = True
                            res += f"✅ {' & '.join([c['nick'] for c in combo])}\n"
                if not f: res += "⚠️ Brak pasujących grup."
                self.send(Message(text=res), thread_id=thread_id, thread_type=thread_type)

        elif m == '!online':
            on = [n.capitalize() for n, s in stan_graczy.items() if s['online']]
            res = "🟢 Online: " + (", ".join(on) if on else "Wszyscy offline.")
            self.send(Message(text=res), thread_id=thread_id, thread_type=thread_type)

        elif m == '!domki':
            nowe = []
            for miasto in MIASTA:
                try:
                    s = BeautifulSoup(requests.get(f"https://www.tibia.com/community/?subtopic=houses&world={SWIAT}&town={miasto}&state=auctioned", headers=HEADERS).text, 'html.parser')
                    for l in s.find_all('a', href=True):
                        if 'page=view&houseid=' in l['href']: nowe.append(f"🏠 {l.text.strip()} ({miasto})")
                except: continue
            res = "🔔 Aukcje: \n" + ("\n".join(nowe[:10]) if nowe else "Brak wolnych domków.")
            self.send(Message(text=res), thread_id=thread_id, thread_type=thread_type)

        elif m == '!konta':
            res = "💳 Status Kont:\n\n"
            for n in LISTA_GRACZY:
                d = get_char_info(n)
                if d:
                    res += f"• {n}: {'Premium 💎' if d['pacc'] else 'Free 🧅'}\n"
            self.send(Message(text=res), thread_id=thread_id, thread_type=thread_type)

        elif m == '!zgony':
            res = []
            for z in LISTA_GRACZY:
                try:
                    d = requests.get(f"https://api.tibiadata.com/v4/character/{z}", headers=HEADERS).json()
                    deaths = d['character'].get('deaths', [])
                    if deaths: res.append(f"💀 {z}: {deaths[0]['reason']}")
                except: continue
            wynik = "🩸 Zgony: \n\n" + ("\n".join(res) if res else "Czysto, nikt nie leżał.")
            self.send(Message(text=wynik), thread_id=thread_id, thread_type=thread_type)

# --- URUCHOMIENIE ---
threading.Thread(target=run_web, daemon=True).start()
threading.Thread(target=szpieg_monitorujacy, daemon=True).start()

# Logowanie przez ciasteczka
bot_client = TibiaBot(" ", " ", session_cookies={"c_user": C_USER, "xs": XS})
bot_client.listen()
