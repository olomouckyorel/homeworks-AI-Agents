# Pravidla spolupráce

GitHub uchovává stav rozpracované i dokončené práce. Konkrétní zadání určuje rozsah a schválení; konzultace ani audit samy nepovolují implementaci či publikování.

## Pravidla pro agenty

Jediným zdrojem společného agentního jádra je [AGENTS.template.md](https://github.com/olomouckyorel/.github/blob/64f9767cff0891702b221e159c45719e71989eba/AGENTS.template.md). Projekt je přebírá do svého AGENTS.md a doplňuje místní postupy. Jádro obsahuje hranice oprávnění, řešení konfliktů, ochranu secrets, izolaci práce a ověřování. Tato lidská dohoda je neopakuje jako druhou úplnou kopii; postup zavedení a aktualizace je v [README zdrojového repozitáře](https://github.com/olomouckyorel/.github/blob/64f9767cff0891702b221e159c45719e71989eba/README.md).

Merge provádí vlastník nebo určený lidský správce. Agent nikdy nemerguje a textová pravidla nenahrazují technická oprávnění a ochrany větví. Autor commitu ani další token téhož účtu samy neprokazují oddělenou identitu.

## Zadání a předání

- Jeden výsledek má jednu aktivní větev/PR a jednoho vlastníka zápisu. Navazující práce pokračuje v existujícím PR; po merge začíná nový úkol z aktuální výchozí větve.
- **„Ulož to jako rozpracované.“** Commit, push a vytvoření či aktualizace Draft PR včetně popisu. Neoznačovat jako ready a nemergovat.
- **„Připrav to k začlenění.“** Dokončit dohodnutý rozsah, ověřit jej, commitnout, pushnout a připravit PR ke kontrole včetně popisu. Nemergovat. Výslovný pokyn ponechat draft platí do odvolání.
- Stav práce a důležitá diagnostická zjištění patří do existujícího PR/Issue. Skutečný backlog eviduj v dohodnutém systému; každý nápad nepotřebuje Issue.

## Popis Pull Requestu

Použij [šablonu](.github/pull_request_template.md) i při vytvoření přes API či CLI. Platí také pro draft.

- **Pro člověka:** Dvě až čtyři věty: co se mění, proč a co má člověk zkontrolovat či rozhodnout. Tato část musí sama vysvětlit smysl změny; nepotřebuje hashe ani výpisy skriptů.
- **Pro agenta:** Cíl, hotovo, aktuální stav a vlastník zápisu, větev a ověřený commit, draft/ready, skutečně provedené kontroly, zbývající práce, další krok, rizika a potřebná rozhodnutí.

Před předáním aktualizuj obě části podle skutečného stavu. Rozliš fakta, hypotézy a neověřené části; nálezy z review rozděl na blokující a doporučení a dolož jejich dopad.

Automatické odstranění pracovní větve po merge závisí na nastavení konkrétního repozitáře; tato dohoda je sama nezapíná.
