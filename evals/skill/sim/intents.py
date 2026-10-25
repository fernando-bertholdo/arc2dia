"""Keyword rules that turn an agent's message into the simulated user's intents.

Deterministic, English and Portuguese. The grader uses the same rules, so "the user was asked
to quit Arc" means exactly what the simulated user reacted to.

A message is split into sentences (. ! ? ; and line breaks) and sentences into clauses
(, : ( ) and dashes). An *action* (quit Arc or Dia, run Dia's import, open Dia, open Arc) is
taken only when the agent asks for it now:

* no negation ("don't", "não"...) and no future or conditional word ("after", "before",
  "until", "if", "I'll", "you'll", "when I", "depois que"...) comes before the keyword in its
  clause, and the clause does not put it off ("later", "another day", "mais tarde"...);
  "once you've / after you / when you" (the user as subject) is allowed;
* and the clause is a request: it holds an explicit marker ("please", "can you", "could you",
  "go ahead and", "you can now", "try again", "por favor", "você pode", "de novo"...) or starts
  with an imperative verb ("Quit Arc", "Open Dia", "Feche o Arc"), or it has the user as subject
  ("once you've quit Arc") and the sentence also asks for a reply ("tell me", "let me know",
  "me avise").
* In a message that asks the user to choose (strategy, options, recommendation, or a plan with a
  question mark), only explicit markers count, so a numbered plan ("2. Quit Arc  4. Run Dia's
  importer  ... Which strategy?") does not make the user act.

Two more ways to ask for the import: the menu path on its own ("In Dia: Dia > Import from
Another Browser > Arc. Ping me when it's done."; not inside a list of 3+ steps, not a sentence
describing what the importer does), and a retry offer in a message about the import ("Shall we
retry?", "you can try once more right away").

Questions are recognised by keywords alone: whether Arc is closed, whether to reset Dia, what
Dia shows, whether the import finished, which strategy to use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

ACTIONS = ("quit_arc", "quit_dia", "run_import", "open_dia", "open_arc")


@dataclass
class Intent:
    name: str
    pos: int
    text: str
    flags: Dict[str, bool] = field(default_factory=dict)


def _w(words: str) -> str:
    """A regex alternation of phrases, matched as whole words."""
    alts = [re.escape(w.strip()).replace(r"\ ", r"\s+") for w in words.split("|") if w.strip()]
    return r"(?<![\w-])(?:" + "|".join(alts) + r")(?![\w-])"


ARC = re.compile(r"(?<![\w-])arc(?![\w-])")
DIA = re.compile(r"(?<![\w-])dia(?![\w-])")

QUIT_VERB = re.compile(_w("quit|quitting|close|closing|shut down|feche|fechar|fecha|encerre|encerrar|saia|sair")
                       + r"|cmd\s*\+\s*q|⌘\s*q|command\s*[-+]\s*q")
IMPORT_WORD = re.compile(_w("import|importer|importing|imports|reimport|re-import|importar|importe|importem|"
                            "importação|importacao|importador|importa|reimportar"))
OPEN_VERB = re.compile(_w("open|reopen|launch|start|abra|abrir|reabra|reabrir|inicie|iniciar"))
NEGATION = re.compile(_w("don't|dont|do not|never|não|nao|nunca|without|sem|avoid|evite|no need to"))
FUTURE = re.compile(_w(
    "later|afterwards|after|before|once|until|till|when|whenever|as soon as|if|i'll|i will|we'll|we will|"
    "you'll|you will|will ask|will need|going to|at the end|in a moment|in a minute|next step|step|then i|"
    "mais tarde|depois que|depois de|depois da|depois do|antes|até|assim que|quando|vou|vamos|você vai|voce vai|iremos|no final|no fim|"
    "daqui a pouco|logo mais|em seguida|passo|etapa|se|so i can|so that|so we can|so the|so it|so your|"
    "para que|para eu|para poder"))
# Words right before "import" that make it the thing being looked at, not something to do.
IMPORT_OBJECT_OF = re.compile(_w(
    "verify|verifying|check|checking|confirm|confirming|compare|review|inspect|see|about|whether|result|results|"
    "status|how|did|verificar|conferir|checar|confirmar|resultado|sobre|como")
    + r"[^.?!]{0,20}$")
# Putting an action off, anywhere in its clause: "run the import later", "try again another day".
DEFERRED = re.compile(_w("later|another day|tomorrow|next time|some other time|in a while|another time|"
                         "outro dia|amanhã|amanha|mais tarde|outra hora|outra vez que"))
USER_AS_SUBJECT = re.compile(_w("once|after|when|as soon as|assim que|depois que|quando")
                             + r"\s+(?:you|você|voce)(?![\w-])")
STRONG = re.compile(_w(
    "please|pls|can you|could you|would you|will you|would you mind|i need you to|go ahead and|"
    "you can now|you may now|you can go ahead|time to|it's time to|right away|try again|retry|once more|"
    "one more time|por favor|você pode|voce pode|você poderia|voce poderia|poderia|pode por favor|"
    "preciso que|já pode|ja pode|hora de|tente|tente novamente|de novo|novamente|outra vez|imediatamente")
    + r"|(?<![\w-])pode\s+(?:fechar|abrir|importar|rodar|fazer|tentar|encerrar|sair|escolher|clicar|executar)")
WEAK = re.compile(_w("tell me|let me know|reply|confirm|ping me|report back|get back to me|me avise|me diga|"
                     "me fala|avise|confirme|responda"))
MENU_PATH = re.compile(r"import\s+from\s+another\s+browser")
DONE_MARKER = re.compile(r"(?:when|once|as\s+soon\s+as)\s+(?:it's|it\s+is|it\s+has|it|you're|you\s+are|you've|you\s+have|"
                         r"the\s+import|done|finished|complete)|quando\s+(?:terminar|acabar|concluir|finalizar)|"
                         r"assim\s+que\s+(?:terminar|acabar)")
DESCRIBES_IMPORTER = re.compile(_w("skips|drops|reads|creates|flattens|keeps|turns|would|does|doesn't|ignores|loses|"
                                   "makes|imports|ignora|cria|lê|descarta|achata|perde"))
LIST_ITEM = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*\u2022])\s")
IMPORT_STATUS = re.compile(
    r"(?<![\w-])(?:did|has|is|was|how\s+did|how's|how\s+is)(?![\w-])[^.?!]{0,30}"
    r"(?<![\w-])(?:the\s+|dia's\s+|your\s+)?import(?:er)?(?![\w-])[^.?!]{0,30}"
    r"(?:finish|finished|done|complete|completed|work|worked|succeed|succeeded|go|going|end|ended)"
    r"|(?:a\s+)?importa(?:ç|c)(?:ã|a)o\s+(?:já\s+)?(?:terminou|funcionou|deu\s+certo|acabou)")
IMPERATIVE = re.compile(r"^(?:" + "|".join(re.escape(v).replace(r"\ ", r"\s+") for v in [
    "quit", "close", "open", "reopen", "run", "choose", "select", "go", "start", "click", "import", "use", "do",
    "try", "retry", "launch", "pick", "make sure", "ensure", "check", "confirm", "keep", "repeat", "redo",
    "feche", "saia", "encerre", "abra", "reabra", "rode", "execute", "escolha", "selecione", "vá", "va",
    "clique", "importe", "use", "faça", "faca", "tente", "inicie", "confira", "confirme", "verifique",
    "mantenha", "repita", "refaça", "garanta", "certifique-se"]) + r")(?![\w-])")
FILLER = re.compile(r"^(?:\d+[.)]|[-*•]|ok|okay|great|good|perfect|alright|all right|thanks|thank you|"
                    r"now|next|then|and|also|first|finally|so|ótimo|otimo|certo|perfeito|obrigado|agora|então|"
                    r"entao|e|também|tambem|primeiro|por fim|beleza)(?![\w-])[\s,.!:]*")
RETRY = re.compile(_w("again|retry|try again|once more|one more time|de novo|novamente|outra vez|tente"))
RETRY_IMPORT = re.compile(_w(
    "retry|try again|try it again|try once more|try one more time|one more try|give it another try|"
    "tentar de novo|tentar novamente|tente de novo|tente novamente|tentar outra vez|nova tentativa"))
PERMISSION_ASK = re.compile(_w("want me to|should i|shall i|can i|may i|let me|do you want me|"
                               "quer que eu|posso|devo|deixa eu"))

QUIT_CHECK = [
    re.compile(r"(?<![\w-])(?:is|has|did|have|was)(?![\w-])[^.?!]{0,25}(?<![\w-])arc(?![\w-])[^.?!]{0,30}"
               r"(?:closed|quit|shut|still\s+(?:open|running)|running|not\s+running)"),
    re.compile(r"(?<![\w-])(?:have|did)\s+you(?![\w-])[^.?!]{0,15}(?:quit|close|closed)[^.?!]{0,15}"
               r"(?<![\w-])arc(?![\w-])"),
    re.compile(r"(?:make\s+sure|ensure|confirm|check|verify|garanta|certifique-se|confirme|verifique)"
               r"[^.?!]{0,40}(?<![\w-])arc(?![\w-])[^.?!]{0,30}"
               r"(?:closed|quit|not\s+running|not\s+open|fechado|encerrado)"),
    re.compile(r"(?<![\w-])arc(?![\w-])[^.?!]{0,20}(?:needs|has|must)\s+to\s+be\s+(?:closed|quit)\s+now"),
    re.compile(r"(?<![\w-])(?:o\s+)?arc(?![\w-])\s+(?:já\s+|ja\s+)?(?:está|esta|foi)\s+(?:fechado|encerrado)\s*\?"),
    re.compile(r"(?<![\w-])arc(?![\w-])\s+ainda\s+(?:está|esta)\s+(?:aberto|rodando)\s*\?"),
    re.compile(r"(?:você|voce)\s+(?:já\s+|ja\s+)?(?:fechou|encerrou|saiu)[^.?!]{0,15}(?<![\w-])arc(?![\w-])"),
]

CHOICE = re.compile(_w(
    "strategy|strategies|estratégia|estrategia|estratégias|estrategias|option|options|opção|opcao|opções|opcoes|"
    "choice|choices|escolhas|which do you|which one|prefer|prefers|preference|prefere|preferência|preferencia|"
    "recommend|recommendation|recommended|recomendo|recomendação|recomendacao|recomendado|"
    "path-names|merge-to-top|to-bookmarks"))
PLAN_WORD = re.compile(_w("plan|plano|proposal|proposta|folders|pastas"))
# What makes a choice about the migration plan (and not, say, about resetting Dia).
PLAN_TOPIC = re.compile(_w(
    "strategy|strategies|estratégia|estrategia|estratégias|folder|folders|pasta|pastas|space|spaces|espaço|espaços|"
    "plan|plano|path-names|merge-to-top|to-bookmarks|bookmarks|bookmarks.html|open tabs|abas abertas|nested|"
    "aninhadas|groups|grupos|imported from edge"))
RESET = re.compile(_w("reset|resetting|fresh|clean slate|start over|from scratch|set aside|aside|"
                      "redefinir|resetar|zerar|do zero|limpo|limpa|nova instalação"))
ASK = re.compile(_w("do you want|would you like|should i|shall i|want me to|prefer|quer|deseja|prefere|gostaria"))
DIA_STATE = re.compile(_w(
    "what do you see|what you see|do you see|can you see|which profiles|what profiles|how many profiles|check in dia|"
    "look in dia|look at dia|o que você vê|o que voce ve|você vê|voce ve|quais perfis|quantos perfis|aparecem|"
    "apareceram"))
DIA_OPEN_CHECK = re.compile(r"(?<![\w-])(?:is|está|esta)\s+(?:o\s+)?dia\s+(?:still\s+|ainda\s+)?"
                            r"(?:open|running|aberto|rodando)|(?<![\w-])(?:o\s+)?dia\s+(?:está|esta)\s+"
                            r"(?:aberto|rodando)\s*\?")
KEEP_DIA_OPEN = re.compile(r"keep\s+(?:a\s+|one\s+)?dia\s+window\s+open|keep\s+dia\s+(?:open|running)|"
                           r"mantenha\s+(?:uma\s+)?janela\s+do\s+dia|deixe\s+o\s+dia\s+aberto")
EDGE = re.compile(r"(?<![\w-])edge(?![\w-])")
BOOKMARKS = re.compile(r"bookmark|marcador|favoritos")
# Importing the exported bookmarks file is a different import from Dia's Arc importer.
BOOKMARK_FILE = re.compile(r"_html?(?![\w-])|bookmarks?\s+(?:html\s+)?file|html\s+file|"
                           r"arquivo\s+(?:html|de\s+favoritos|de\s+marcadores)")
TERMINAL_REQ = [
    re.compile(r"(?:in|on|open|abra|no)\s+(?:the\s+|o\s+|your\s+)?terminal"),
    re.compile(r"(?<![\w-])(?:run|paste|type|execute|rode|cole|digite)(?![\w-])[^.?!]{0,30}"
               r"(?:this|these|the\s+following|este|estes|o\s+seguinte)\s+(?:command|commands|comando|comandos)"),
]
TERMINAL_EXCUSE = re.compile(_w("allow|permit|permission|permitir|permissão|automation|automação|control"))
OPEN_ARC_BLOCK = re.compile(_w("after|until|till|once|when|before|only|if|não|nao|don't|dont|do not|never|"
                               "depois|até|quando|antes|só|somente|apenas|se|yet|ainda|so"))


# An answer menu: two or more option lines plus a cue to pick one ("Reply with one of these",
# "Please choose", "A or B"). Actions written inside the options ("A. Retry the swap, then you run
# the import again") are not requests: the user picks an option instead.
OPTION_LINE = re.compile(
    r"(?m)^[ \t]*(?:[-*•][ \t]*)?(?:(?:option|opção|opcao)[ \t]+)?"
    r"(?:\(?(?P<letter>[a-d1-4])[.):][ \t]+|\"(?P<quoted>[^\"\n]{2,40})\"[ \t]*[:–—-][ \t]*)(?P<text>.+)$")
MENU_CUE = re.compile(_w(
    "reply with|respond with|answer with|choose|pick|select|one of these|which option|which one|the letter|"
    "a or b|a/b|escolha|responda com|qual opção|qual opcao|uma destas|uma dessas|uma das opções|uma das opcoes"))
OPTION_GOOD = re.compile(_w(
    "retry|try again|continue|proceed|go ahead|apply|yes|do it|finish|resume|run the swap|redo|"
    "continuar|prosseguir|tentar|tente|sim|seguir|refazer|aplicar"))
OPTION_BAD = re.compile(_w(
    "stop|cancel|abort|leave everything|nothing else|give up|end here|quit the migration|"
    "parar|pare|cancelar|abortar|desistir|deixar como está|deixar como esta"))
OPTION_REC = re.compile(_w("recommended|recommend|recomendado|recomendo|recomendada"))
# "Do you want me to retry the swap, or stop here?" without a menu.
CONTINUE_OR_STOP = re.compile(
    r"(?:retry|try again|continue|proceed|go on|keep going|tentar|continuar|prosseguir)[^?]{0,80}"
    r"(?<![\w-])(?:or|ou)(?![\w-])[^?]{0,40}(?:stop|cancel|abort|leave|parar|cancelar|deixar)")


def menu(message: str):
    """The options of an answer menu, or [] when the message has none."""
    msg = normalize(message)
    opts = [m for m in OPTION_LINE.finditer(msg)]
    if len(opts) < 2 or not MENU_CUE.search(msg):
        return []
    return opts


def pick_option(opts) -> Tuple[str, str]:
    """The option the simulated user picks: the recommended one, else the one that carries on."""
    def score(m):
        t = (m.group("quoted") or "") + " " + m.group("text")
        return (6 if OPTION_REC.search(t) else 0) + (2 if OPTION_GOOD.search(t) else 0) - (3 if OPTION_BAD.search(t) else 0)
    best = max(opts, key=score)  # max keeps the first of equal scores
    label = best.group("letter") or best.group("quoted")
    return label, best.group("text").strip()


def normalize(text: str) -> str:
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("…", " ").replace(" ", " ")
    t = re.sub(r"\.{2,}", " ", t)
    t = re.sub(r"\.(html?|json|pyz|md|txt)(?![\w-])", r"_\1", t)  # keep file names in one sentence
    t = re.sub(r"\b(e\.g|i\.e|etc|vs|approx)\.", r"\1", t, flags=re.I)
    t = t.replace("`", "").replace("*", "").replace("#", " ")
    return t.lower()


def sentences(text: str) -> List[Tuple[int, str]]:
    out = []
    for m in re.finditer(r"[^.!?;\n]+[.!?;]*", text):
        if m.group(0).strip():
            out.append((m.start(), m.group(0)))
    return out


def clauses(sentence: str) -> List[Tuple[int, str]]:
    out = []
    for m in re.finditer(r"[^,:()–—]+", sentence):
        if m.group(0).strip(" -"):
            out.append((m.start(), m.group(0)))
    return out


def _strip_filler(clause: str) -> str:
    c = clause.strip()
    for _ in range(4):
        new = FILLER.sub("", c, count=1).strip()
        if new == c:
            break
        c = new
    return c


def _blocked(clause: str, at: int) -> bool:
    """A negation or a future/conditional word before position ``at`` of the clause, or the action
    put off anywhere in it."""
    head = clause[:at]
    if NEGATION.search(head) or DEFERRED.search(clause):
        return True
    return bool(FUTURE.search(USER_AS_SUBJECT.sub(" ", head)))


def _requested(clause: str, sentence: str, choice: bool) -> bool:
    if STRONG.search(clause) or PERMISSION_ASK.search(clause):
        return True
    if choice:
        return False
    core = _strip_filler(clause)
    if IMPERATIVE.match(core):
        return True
    return bool(USER_AS_SUBJECT.match(core) and (STRONG.search(sentence) or WEAK.search(sentence)))


def _target(clause: str, sentence: str, message: str) -> str:
    for scope in (clause, sentence):
        arc, dia = bool(ARC.search(scope)), bool(DIA.search(scope))
        if arc and dia:
            return "both"
        if arc:
            return "arc"
        if dia:
            return "dia"
    if DIA.search(message) and not ARC.search(message):
        return "dia"
    return "arc"


def is_choice(msg: str) -> bool:
    if CHOICE.search(msg):
        return True
    return bool(PLAN_WORD.search(msg) and "?" in msg)


def classify(message: str) -> List[Intent]:
    msg = normalize(message)
    choice = is_choice(msg)
    found: Dict[str, Intent] = {}

    def add(name: str, pos: int, text: str, **flags) -> None:
        if name not in found or pos < found[name].pos:
            found[name] = Intent(name, pos, text.strip(), dict(flags))

    if choice:
        m = CHOICE.search(msg) or PLAN_WORD.search(msg)
        add("choice", m.start() if m else 0, msg[:200],
            edge_offered=bool(EDGE.search(msg) and BOOKMARKS.search(msg)),
            about_plan=bool(PLAN_TOPIC.search(msg)))

    opts = menu(message)
    if opts:
        label, text = pick_option(opts)
        add("pick_option", opts[0].start(), msg[opts[0].start():opts[-1].end()], label=label, option=text)
        for m in opts:  # keep positions, drop the option text
            msg = msg[:m.start()] + " " * (m.end() - m.start()) + msg[m.end():]
    elif CONTINUE_OR_STOP.search(msg) and "?" in msg:
        m = CONTINUE_OR_STOP.search(msg)
        add("pick_option", m.start(), m.group(0), label="", option="continue")

    for s_pos, sent in sentences(msg):
        has_import = bool(IMPORT_WORD.search(sent))
        for rx in QUIT_CHECK:
            m = rx.search(sent)
            if m and not NEGATION.search(sent[:m.start()]):
                add("quit_arc", s_pos + m.start(), sent, check=True)
                break
        m = RESET.search(sent)
        if m and DIA.search(sent) and ("?" in sent or ASK.search(sent)):
            add("reset_dia", s_pos + m.start(), sent)
        m = DIA_STATE.search(sent)
        if m:
            add("dia_state", s_pos + m.start(), sent)
        m = IMPORT_STATUS.search(sent)
        if m and "?" in sent:
            add("import_status", s_pos + m.start(), sent)
        m = DIA_OPEN_CHECK.search(sent)
        if m and not NEGATION.search(sent[:m.start()]):
            add("open_dia", s_pos + m.start(), sent, check=True)
        if not TERMINAL_EXCUSE.search(sent):
            for rx in TERMINAL_REQ:
                m = rx.search(sent)
                if m:
                    add("run_command", s_pos + m.start(), sent)
                    break

        live = [(s_pos + c_pos, clause) for c_pos, clause in clauses(sent) if _requested(clause, sent, choice)]
        # A question about resetting Dia mentions the import only as context ("...so the import starts
        # clean?"), and importing bookmarks.html is not Dia's Arc import.
        reset_here = "reset_dia" in found and found["reset_dia"].pos >= s_pos
        bookmark_file = bool(BOOKMARK_FILE.search(sent))
        import_here = reset_here or bookmark_file
        for base, clause in live:
            m = IMPORT_WORD.search(clause)
            if m and not _blocked(clause, m.start()) and not IMPORT_OBJECT_OF.search(clause[:m.start()]):
                if bookmark_file:
                    add("import_bookmarks", base + m.start(), sent)
                elif not reset_here:
                    add("run_import", base + m.start(), sent, retry=bool(RETRY.search(sent)))
                    import_here = True
        # "In Dia: Dia > Import from Another Browser > Arc. Ping me when it's done." (a menu path as the
        # instruction), unless it is one item of a multi-step list or the message asks for a choice.
        m = MENU_PATH.search(sent)
        if m and not import_here and not choice and len(LIST_ITEM.findall(message)) < 3 \
                and not _blocked(sent, m.start()) and not IMPORT_OBJECT_OF.search(sent[:m.start()]) \
                and not DESCRIBES_IMPORTER.search(sent):
            here = [s for p, s in sentences(msg) if p >= s_pos][:2]
            if any(STRONG.search(x) or (WEAK.search(x) and DONE_MARKER.search(x)) for x in here):
                add("run_import", s_pos + m.start(), sent, retry=bool(RETRY.search(sent)))
                import_here = True
        # "Shall we retry?" / "you can try once more right away" in a message about the import
        if not import_here and IMPORT_WORD.search(msg):
            for c_pos, clause in clauses(sent):
                m = RETRY_IMPORT.search(clause)
                if m and not _blocked(sent, c_pos + m.start()) and ("?" in sent or _requested(clause, sent, choice)):
                    add("run_import", s_pos + c_pos + m.start(), sent, retry=True)
                    import_here = True
                    break
        for base, clause in live:
            m = QUIT_VERB.search(clause)
            if m and not _blocked(clause, m.start()):
                target = _target(clause, sent, msg)
                ask = bool(PERMISSION_ASK.search(clause[:m.start()]))
                if target in ("arc", "both"):
                    add("quit_arc", base + m.start(), sent, permission_ask=ask)
                if target in ("dia", "both") and not has_import:
                    add("quit_dia", base + m.start(), sent, permission_ask=ask)
            m = OPEN_VERB.search(clause)
            if m and not _blocked(clause, m.start()) and not PERMISSION_ASK.search(clause[:m.start()]):
                rest = clause[m.end():m.end() + 25]
                if DIA.search(rest) and not import_here:
                    add("open_dia", base + m.start(), sent)
                elif ARC.search(rest) and not OPEN_ARC_BLOCK.search(sent):
                    add("open_arc", base + m.start(), sent)
            m = KEEP_DIA_OPEN.search(clause)
            if m and not _blocked(clause, m.start()):
                add("open_dia", base + m.start(), sent)

    return sorted(found.values(), key=lambda i: i.pos)


def names(message: str) -> List[str]:
    return [i.name for i in classify(message)]
