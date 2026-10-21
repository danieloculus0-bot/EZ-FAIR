"""Lab030: 3,000 synthetic EZ-FAIR extraction cases scored by a BEAN Q-policy.

Exercises the actual extractor_engine.extract_pdf_dimensions on vector PDFs.
Train 2000, evaluate 1000 disjoint case IDs with frozen Q values. All inputs,
predictions, oracle values, decisions, and rewards are losslessly archived.
This is strategy selection from predeclared rules, NOT learned neural vision.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import random
import re
from pathlib import Path

import fitz
from extractor_engine import TITLE_BLOCK_DEFAULTS, extract_pdf_dimensions

ACTIONS = ("existing", "scoped", "review")
SCENARIOS = ("pair", "asymmetric", "symmetric", "defaults", "admin", "reference", "unresolved", "radius", "unlabeled")
NUM = r"(?:\d+\.\d+|\.\d+|\d+)"
FEATURE = re.compile(r"\b(?:WIDTH|LENGTH|DEPTH|HEIGHT)\s+(?P<nom>" + NUM + r")(?P<tol>\s*\+\s*(?P<plus>" + NUM + r")\s*/\s*-\s*(?P<minus>" + NUM + r")|\s*(?:±|\+/-)\s*(?P<sym>" + NUM + r"))?", re.I)

def encode(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
def sha(value): return hashlib.sha256(value).hexdigest()
def triple(n, low, high): return [round(n,6),round(low,6),round(high,6)]

def fixture(i, seed):
    rnd=random.Random(seed*100003+i*7919)
    scenario=SCENARIOS[i%len(SCENARIOS)]
    x=round(rnd.uniform(.2,99.8),3)
    y=round(rnd.uniform(.2,99.8),3)
    if scenario=="pair":
        line=f"WIDTH {x:.3f} +.010/-.005 LENGTH {y:.3f} +.020/-.010"
        expected=[triple(x,x-.005,x+.010),triple(y,y-.010,y+.020)]
    elif scenario=="asymmetric":
        line=f"DEPTH {x:.3f} +.012/-.007"
        expected=[triple(x,x-.007,x+.012)]
    elif scenario=="symmetric":
        line=f"HEIGHT {x:.3f} +/-.025"
        expected=[triple(x,x-.025,x+.025)]
    elif scenario=="defaults":
        line=f"WIDTH {x:.2f} LENGTH {y:.3f}"
        xx=round(x,2)
        expected=[triple(xx,xx-.02,xx+.02),triple(y,y-.005,y+.005)]
    elif scenario=="admin":
        line=f"DWG NO {rnd.randint(1200,9980)}.{rnd.randint(100,999)} REV B"
        expected=[]
    elif scenario=="reference":
        line=f"REF ({x:.3f})"
        expected=[]
    elif scenario=="unresolved":
        line=f"SIZE {x:.3f} TOL SEE NOTE 7"
        expected=[]
    elif scenario=="radius":
        line=f"R{x:.3f}"
        expected=[triple(x,x-.005,x+.005)]
    else:
        xx=round(x,2)
        line=f"{xx:.2f} X {y:.3f}"
        expected=[triple(xx,xx-.02,xx+.02),triple(y,y-.005,y+.005)]
    return {"id":f"EFC-{i:04d}","line":line,"scenario":scenario,
            "expected":expected,"needs_review":scenario=="unresolved"}

def scoped(line):
    if "TOL SEE NOTE" in line:return [],True
    if re.search(r"\b(?:DWG|DRAWING|REV|SHEET|DATE|REF)\b",line,re.I):return [],False
    found=[]
    for match in FEATURE.finditer(line):
        raw=match.group("nom");n=float(raw)
        if match.group("plus") is not None:
            lower=n-float(match.group("minus"));upper=n+float(match.group("plus"))
        elif match.group("sym") is not None:
            lower=n-float(match.group("sym"));upper=n+float(match.group("sym"))
        else:
            places=len(raw.split(".",1)[1]) if "." in raw else 0
            tolerance=(TITLE_BLOCK_DEFAULTS["three_place"] if places>=3 else
                       TITLE_BLOCK_DEFAULTS["two_place"] if places>0 else
                       TITLE_BLOCK_DEFAULTS["whole_number"])
            lower=n-tolerance;upper=n+tolerance
        found.append(triple(n,lower,upper))
    return found,False

def features(line):
    # Only visible text: oracle label/scenario never enters the model's input.
    bits=(bool(re.search(r"\b(?:DWG|REV|SHEET|DATE)\b",line)),
          bool(re.search(r"\bREF\b",line)), "TOL SEE NOTE" in line,
          len(FEATURE.findall(line))>=2,
          bool(re.search(r"\+\s*\.\d+\s*/\s*-",line)),
          "+/-" in line)
    return ":".join(str(int(x)) for x in bits)

def evaluate(expected,prediction,needs_review=False,reviewed=False):
    remaining=list(expected);extras=0
    for value in prediction:
        if value in remaining: remaining.remove(value)
        else:extras+=1
    missed=len(remaining)
    exact=not extras and not missed and (not needs_review or reviewed)
    if reviewed: reward=2.0 if needs_review else (-2.5 if expected else -.3)
    else:reward=4.0*int(exact)-3.0*extras-2.0*missed-(2.0 if needs_review else 0.0)
    return {"exact":bool(exact),"false_balloons":extras,
            "missing_or_wrong_limits":missed,"reward":round(reward,3),"reviewed":bool(reviewed)}

class BeanQ:
    """One-step terminal Q-learning; rewards from evaluator, no weights of an LLM."""
    def __init__(self,seed):
        self.rng=random.Random(seed);self.q={};self.games=0;self.correct=0;self.reward_total=0.
    def choose(self,state,epsilon):
        q=self.q.setdefault(state,[0.]*len(ACTIONS))
        if self.rng.random()<epsilon:return self.rng.randrange(len(ACTIONS))
        return max(range(len(ACTIONS)),key=lambda a:(q[a],-a))
    def learn(self,state,action,reward):
        q=self.q[state]
        q[action]=round(q[action]+.23*(reward-q[action]),8)
        self.games+=1;self.reward_total+=reward
    def scoreboard(self):
        return {"games":self.games,"correct":self.correct,
                "total_reward":round(self.reward_total,3),"q":self.q}

def extract_actual(cases,folder):
    folder.mkdir(parents=True,exist_ok=True);out={}
    for start in range(0,len(cases),100):
        sub=cases[start:start+100]
        doc=fitz.open()
        for case in sub:
            page=doc.new_page(width=620,height=160)
            page.insert_text((40,72),case["line"],fontname="helv",fontsize=10)
        pdf=folder/f"batch-{start//100:02d}.pdf"
        doc.save(pdf);doc.close()
        characteristics=extract_pdf_dimensions(pdf)
        by_page={index:[] for index in range(len(sub))}
        for ch in characteristics:
            by_page[ch.page_index].append(triple(ch.nominal,ch.lsl,ch.usl))
        for index,case in enumerate(sub):
            out[case["id"]]=by_page[index]
        pdf.unlink()
    return out

def total(records,name):
    rows=[e[name]["score"] for e in records]
    return {"cases":len(rows),"exact":sum(r["exact"] for r in rows),
            "false_balloons":sum(r["false_balloons"] for r in rows),
            "missing_or_wrong_limits":sum(r["missing_or_wrong_limits"] for r in rows),
            "reviews":sum(r["reviewed"] for r in rows),
            "reward":round(sum(r["reward"] for r in rows),3)}

def execute(output,seed=20261020):
    count=3000;training=2000
    cases=[fixture(i,seed+(0 if i<training else 700000)) for i in range(count)]
    baseline=extract_actual(cases,output/"temporary-vector-pdfs")
    agent=BeanQ(seed)
    events=[]
    for index,case in enumerate(cases):
        learn=index<training
        state=features(case["line"])
        predecision = {
            "games": agent.games, "exact": agent.correct,
            "reward_total": round(agent.reward_total,3),
            "current_q": list(agent.q.get(state,[0.]*len(ACTIONS))),
        }
        score_seen=sha(encode(predecision))
        action=agent.choose(state,.20 if learn else 0.)
        proposed,ask_review=scoped(case["line"])
        strategies={"existing":(baseline[case["id"]],False),"scoped":(proposed,ask_review),
                    "review":([],True)}
        attempts={}
        for name,(prediction,reviewed) in strategies.items():
            attempts[name]={"prediction":prediction,"score":evaluate(
                case["expected"],prediction,case["needs_review"],reviewed)}
        chosen=ACTIONS[action]
        outcome=attempts[chosen]["score"]
        if learn:
            agent.learn(state,action,outcome["reward"])
            agent.correct+=int(outcome["exact"])
        events.append({"id":case["id"],"cohort":"training" if learn else "holdout",
                       "source_text":case["line"],"scenario":case["scenario"],
                       "oracle":case["expected"],"needs_review":case["needs_review"],
                       "q_state":state,"scoreboard_seen":predecision,
                       "scoreboard_seen_sha256":score_seen,
                       "chosen_action":chosen,"q_after":list(agent.q[state]),
                       **attempts,"bean":attempts[chosen]})
    policy=encode(agent.scoreboard())
    output.mkdir(parents=True,exist_ok=True)
    (output/"q-policy.json.gz").write_bytes(gzip.compress(policy,mtime=0))
    # All attempts and failures, NOT just a success count.
    raw=b"".join(encode(e)+b"\n" for e in events)
    archive=gzip.compress(raw,compresslevel=9,mtime=0)
    (output/"events.jsonl.gz").write_bytes(archive)
    report={"schema":"bean.ezfair.extraction.lab030.v1","seed":seed,
            "source":"real EZ-FAIR extractor_engine.extract_pdf_dimensions",
            "training":training,"holdout":count-training,"total_cases":count,
            "train_scores":{a:total(events[:training],a) for a in ("existing","scoped","review","bean")},
            "holdout_scores":{a:total(events[training:],a) for a in ("existing","scoped","review","bean")},
            "q_states":len(agent.q),"q_updates":agent.games,"q_policy_sha256":sha(policy),
            "event_archive_sha256":sha(archive),"event_bytes_sha256":sha(raw),
            "research_classification":"synthetic vector PDFs, not real drawing validation or neural training",
            "limitations":"BEAN chooses from predeclared strategies; oracle values never shown before a decision"}
    (output/"scoreboard.json").write_bytes(encode(report)+b"\n")
    return report

def verify(folder):
    report=json.loads((folder/"scoreboard.json").read_bytes())
    compressed=(folder/"events.jsonl.gz").read_bytes()
    if sha(compressed)!=report["event_archive_sha256"]:raise ValueError("bad archive hash")
    raw=gzip.decompress(compressed)
    if sha(raw)!=report["event_bytes_sha256"]:raise ValueError("bad content hash")
    rows=[json.loads(line) for line in raw.splitlines()]
    if len(rows)!=3000:raise ValueError("missing test results")
    state_q={}
    observed_games=observed_exact=0
    observed_reward=0.0
    for i,row in enumerate(rows):
        original=fixture(i,report["seed"]+(0 if i<2000 else 700000))
        if (row["id"]!=original["id"] or row["source_text"]!=original["line"]
            or row["oracle"]!=original["expected"] or row["needs_review"]!=original["needs_review"]
            or row["scenario"]!=original["scenario"]):
            raise ValueError("incorrect fixture truth or input: "+row["id"])
        qstate=row["q_state"]
        if qstate!=features(row["source_text"]):
            raise ValueError("incorrect state: "+row["id"])
        existing=state_q.setdefault(qstate,[0.]*len(ACTIONS))
        scoreboard={"games":observed_games,"exact":observed_exact,
                    "reward_total":round(observed_reward,3),"current_q":list(existing)}
        if row["scoreboard_seen"]!=scoreboard or row["scoreboard_seen_sha256"]!=sha(encode(scoreboard)):
            raise ValueError("invalid pre-decision scoreboard: "+row["id"])
        for action in ("existing","scoped","review"):
            candidate=row[action]
            if candidate["score"]!=evaluate(row["oracle"],candidate["prediction"],row["needs_review"],candidate["score"]["reviewed"]):
                raise ValueError("tampered result: "+row["id"])
        if row["bean"]!=row[row["chosen_action"]]:raise ValueError("wrong BEAN score")
        if i<2000:
            a=ACTIONS.index(row["chosen_action"])
            reward=row["bean"]["score"]["reward"]
            existing[a]=round(existing[a]+.23*(reward-existing[a]),8)
            observed_games+=1
            observed_exact+=int(row["bean"]["score"]["exact"])
            observed_reward+=reward
        if row["q_after"]!=existing:raise ValueError("Q-update replay diverged: "+row["id"])
    for cohort,name in ((rows[:2000],"train_scores"),(rows[2000:],"holdout_scores")):
        for action in ("existing","scoped","review","bean"):
            if total(cohort,action)!=report[name][action]:raise ValueError("tampered summary")
    if sha(gzip.decompress((folder/"q-policy.json.gz").read_bytes()))!=report["q_policy_sha256"]:
        raise ValueError("tampered Q policy")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("lab030-evidence"))
    parser.add_argument("--verify",action="store_true")
    arguments=parser.parse_args()
    result=verify(arguments.output) if arguments.verify else execute(arguments.output)
    print(json.dumps({"verified":bool(arguments.verify),"scoreboard":result},indent=2))
