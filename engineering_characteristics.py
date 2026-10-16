"""Engineering-aware characteristic review for EZ-FAIR vector PDFs.

Runs after the existing numeric extractor. This is deliberately conservative:
unknown limits and unreadable leader/FCF symbols are flagged, never invented.
Uses original PDF geometry; no OCR and no uploaded drawing content.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

import extractor_engine as base
try:
    from extractor_fraction_weld_patch import extract_pdf_dimensions as _legacy_extract
except ImportError:
    from extractor_precision_patch import extract_pdf_dimensions as _legacy_extract
from extractor_engine import Characteristic, SkippedCandidate
from extractor_precision_patch import add_pdf_balloons

# CAD fonts often omit the ± glyph from selectable text. An unsigned side-by-side
# tolerance is never silently considered confirmed.
SIGNED = re.compile(r'([+\-])\s*(\.\d+|\d+\.\d+)')
PLUS_MINUS = re.compile(r'(?:±|\+\s*/\s*-|\+\s*-|\+\s*or\s*-)\s*(\.\d+|\d+\.\d+)', re.I)
NUM = re.compile(r'(?<![\w.])(?:\d+\.\d+|\.\d+)(?!\w)')
THREAD = re.compile(r'(?<!\d)(?P<size>\d+\s*/\s*\d+|\d*\.\d+|\d+)\s*["”]?\s*[-–]\s*(?P<tpi>\d+)\s*(?P<family>UNC|UNF|UNEF|NPT|NPTF)\s*(?:[-\s]*(?P<class>[123][AB]))?', re.I)
GDTS = re.compile(r'[⌖⏥⌔⟂∥⌭◎⌯⌓⏤⏧]|\b(?:POSITION|FLATNESS|PROFILE OF (?:A )?SURFACE|PERPENDICULARITY|PARALLELISM|CONCENTRICITY|RUNOUT)\b',re.I)
ADMIN_LINE = re.compile(r'\b(?:SCALE|REVISION|DRAWN BY|DWG\.?\s*NO|ISSUED DATE|CONTROLLED DOCUMENT|PREPRODUCTION|PROPRIETARY|MCMASTER-CARR\s*P/N)\b',re.I)


@dataclass(frozen=True)
class SheetRules:
    two: float | None = None
    three: float | None = None
    angular: float | None = None
    fraction: float | None = None
    source: str = 'not confidently extracted'


def parse_sheet_rules(page: fitz.Page) -> SheetRules:
    """Read title-block defaults without turning its cells into balloons."""
    words = sorted((w for w in page.get_text('words') if w[1] > page.rect.height * .81), key=lambda w: (round(w[1] / 5), w[0]))
    tol_heading = next((w for w in words if 'TOLERANCES' in w[4].upper()), None)
    if not tol_heading:
        return SheetRules()
    # Follow the table's actual columns rather than searching arbitrary page text.
    left, top = tol_heading[0], tol_heading[1]
    cells = [w for w in words if left - 15 <= w[0] <= left + 120 and top <= w[1] <= top + 75]
    def beside(key: str) -> str | None:
        labels = [w for w in cells if w[4].upper() == key.upper()]
        if not labels:
            return None
        w = labels[0]
        values = [c for c in cells if c[0] > w[2] - 1 and abs(c[1] - w[1]) <= 4 and re.fullmatch(r'(?:\d+/\d+|\d*\.\d+)', c[4])]
        return sorted(values,key=lambda c:c[0])[0][4] if values else None
    def scalar(v):
        try: return float(v) if v is not None else None
        except ValueError: return None
    frac = beside('X/Y')
    fv = None
    if frac and re.fullmatch(r'\d+/\d+',frac):
        a,b = map(int,frac.split('/'))
        fv = a/b if b else None
    # CAD tolerance angular symbol can be vector-only. A lone scalar directly
    # underneath .XXX's tolerance cell is an *indication*, requiring review.
    angular = None
    triple_label = next((w for w in cells if w[4].upper() == '.XXX'),None)
    if triple_label:
        next_row = [c for c in cells if triple_label[1]+9 < c[1] < triple_label[1]+28 and c[0] >= triple_label[2] and re.fullmatch(r'\d*\.\d+',c[4])]
        if len(next_row) == 1: angular = float(next_row[0][4])
    two,three = scalar(beside('.XX')),scalar(beside('.XXX'))
    return SheetRules(two, three, angular, fv, 'drawing title-block tolerance table')


def region_reason(page: fitz.Page, rect: fitz.Rect, source: str) -> str | None:
    """Exclude template regions, keeping dimensional areas and separately reviewed notes."""
    x,y = rect.x0,rect.y0
    w,h = page.rect.width,page.rect.height
    if y >= h * .85:
        return 'revision history / title block / drawing footer'
    if x >= w * .88 and y >= h * .37:
        return 'document control side stamp'
    if x >= w * .70 and y < h * .29 and re.search(r'\bITEM\s+QTY\b', page.get_text('text', clip=fitz.Rect(w*.68,0,w,h*.12)),re.I):
        return 'bill of materials'
    if ADMIN_LINE.search(source) and not re.search(r'\b(?:THREAD|WELD|THRU|HOLE|RADIUS|PLACES)\b',source,re.I):
        return 'administrative annotation'
    return None


def _c_rect(c: Characteristic) -> fitz.Rect:
    return fitz.Rect(c.rect)


def _skip(skipped: list[SkippedCandidate], c: Characteristic, reason: str) -> None:
    skipped.append(SkippedCandidate(c.page_index, str(c.raw_text),reason,c.rect,str(c.metadata.get('source',''))[:240]))


def _is_modifier(candidate: Characteristic, group: list[Characteristic]) -> bool:
    """The .005, -.015, .003 beside G/H are modifiers, not inspection rows."""
    if not isinstance(candidate.nominal,(float,int)) or candidate.nominal > .2:
        return False
    a = _c_rect(candidate)
    src = str(candidate.metadata.get('source','')).strip()
    # Never drop a legitimate small geometric dimension just because of size.
    if not (src.startswith(('+','-')) or re.search(r'(?<!\w)\d+\.\d+\s*[+\-]\s*\.\d+',src) or re.search(r'(?<!\w)\d+\.\d+\s+\.\d+\s*$',src)):
        return False
    for parent in group:
        if parent is candidate or not isinstance(parent.nominal,(int,float)) or parent.nominal < 0.3:
            continue
        b = _c_rect(parent)
        if abs(a.y0-b.y0) < 23 and (a.x0 <= b.x1+35 and a.x1 >= b.x0-10):
            return True
    return False


def _nearby_words(page:fitz.Page,rect:fitz.Rect,pad_x=30,pad_y=13)->list[tuple]:
    box=fitz.Rect(rect.x0-pad_x,rect.y0-pad_y,rect.x1+pad_x,rect.y1+pad_y) & page.rect
    return sorted((w for w in page.get_text('words') if fitz.Rect(w[:4]).intersects(box)),key=lambda w:(w[1],w[0]))


def _explicit_limits(c: Characteristic, page: fitz.Page) -> tuple[float,float,str,bool] | None:
    """Interpret tolerance only when spatially associated to the same nominal."""
    if not isinstance(c.nominal,(int,float)):
        return None
    a = _c_rect(c)
    neighbors = _nearby_words(page,a,30,13)
    # Prefer a single CAD word carrying nominal + tolerance, e.g. 11.990+.005.
    source = str(c.metadata.get('source',''))
    same = [w[4] for w in neighbors if abs(w[1]-a.y0)<14 and w[0] >= a.x0-3 and w[0] <= a.x1+27]
    text=' '.join(same)
    if c.nominal >= 1 and (('+' in source or '±' in source) or ('+' in text or '±' in text)):
        # Do not accept one sign without its opposite unless complete nominal ± case.
        blob = source+' '+text
        pm = PLUS_MINUS.search(blob)
        if pm:
            v=float(pm.group(1))
            return round(c.nominal-v,6),round(c.nominal+v,6),'explicit symmetric callout',False
        plus = re.search(r'\+\s*(\.\d+|\d+\.\d+)',blob)
        minus = re.search(r'(?<!\w)-\s*(\.\d+|\d+\.\d+)',blob)
        if plus and minus:
            p,m = float(plus.group(1)),float(minus.group(1))
            return round(c.nominal-m,6),round(c.nominal+p,6),'explicit asymmetric callout',False
    # Often the CAD font drops +/- from the text layer, leaving "3.504 .003".
    # Use the apparent limits as provisional, and tell QE to confirm visually.
    if c.nominal >= 1 and re.search(r'^\d+\.\d{3,4}\s+\.\d{2,4}$',source):
        nums = re.findall(r'\.\d+',source)
        if nums:
            v=float(nums[-1])
            if v < .1:
                return round(c.nominal-v,6),round(c.nominal+v,6),'inferred symmetric tolerance; +/- glyph not recoverable',True
    return None


def _default_limits(c:Characteristic,rules:SheetRules)->tuple[float|str,float|str,str,bool]:
    raw=str(c.raw_text)
    if not isinstance(c.nominal,(int,float)):
        return '', '', 'nonnumeric requirement', True
    if re.search(r'(?<!\w)\d+\s*/\s*\d+',raw):
        tol=rules.fraction
        source='general fractional tolerance'
    elif c.type in {'°','ANGLE'} or '°' in raw:
        tol=rules.angular
        source='general angular tolerance (symbol confirm)'
    else:
        # Numeric precision from original token; values such as 11.990 must
        # retain trailing zeroes rather than relying on float representation.
        mt=re.search(r'\d*\.(\d+)',raw)
        digits=len(mt.group(1)) if mt else 0
        tol=rules.two if digits==2 else rules.three if digits==3 else None
        source='general title-block tolerance'
    if tol is None:
        return '', '', 'NO VERIFIED APPLICABLE TOLERANCE', True
    return round(c.nominal-tol,6),round(c.nominal+tol,6),source,source.startswith('general angular')


def _thread_features(page:fitz.Page, page_i:int, pdf_name:str, skipped:list[SkippedCandidate])->list[Characteristic]:
    result=[]
    for line,rect,_ in base._line_groups(page):
        m=THREAD.search(line)
        if not m or region_reason(page,rect,line):continue
        core=m.group(0).strip()
        # The entire thread specification is one categorical requirement.
        nearby = _nearby_words(page,rect,25,30)
        complement = [str(w[4]) for w in nearby if w[1] > rect.y1 and w[1] < rect.y1 + 28 and any(k in str(w[4]).upper() for k in ('MASK','COATING','THRU','START'))]
        label=line.strip() + (' | '+ ' '.join(complement) if complement else '')
        feature=Characteristic(0,base._reference_location(page,rect,page_i),core,'','', 'THREAD',page_i,tuple(rect),label,'THREAD GAGE','Verify complete thread, class, quantity, direction and depth on print','',{'source':line,'drawing_name':pdf_name,'interpretation':'grouped thread callout','review_required':True})
        result.append(feature)
    return result


def _thread_part(c:Characteristic,threads:list[Characteristic])->bool:
    # Thread dimension token alone must not create separate FAI rows.
    a=_c_rect(c)
    for th in threads:
        b=_c_rect(th)
        if a.intersects(fitz.Rect(b.x0-12,b.y0-5,b.x1+12,b.y1+8)):
            return True
    return False




def _gdt_features(page:fitz.Page,page_i:int,pdf_name:str)->list[Characteristic]:
    """Protect readable FCF text as a single categorical requirement.

    Does not claim to decode vector-only symbols, feature association, or datums.
    """
    result=[]
    for line,rect,_ in base._line_groups(page):
        if not GDTS.search(line) or region_reason(page,rect,line):continue
        # Never turn a general explanatory drawing note into a false GD&T frame.
        if re.search(r'\b(?:ANSI|STANDARD|GENERAL|NOTE|DEFINITION)\b',line,re.I):continue
        result.append(Characteristic(0,base._reference_location(page,rect,page_i),'SEE PRINT','','','GD&T',page_i,tuple(rect),line.strip(),'CMM / APPROPRIATE GAGE','VERIFY FCF / DATUMS / MODIFIERS / LEADER','',{'source':line,'drawing_name':pdf_name,'review_required':True,'interpretation':'visible GD&T text; datum and leader association unverified'}))
    return result

def _manufacturing_notes(page: fitz.Page, page_i:int, pdf_name:str)->list[Characteristic]:
    """Capture only clear manufacturing instructions, never the note index as a dimension."""
    lines=list(base._line_groups(page))
    found=[]
    keys=('INDICATED SURFACES TO BE MACHINED','MASK SURFACES BEFORE COATING','WELD TO START AT BASE PLATE')
    for line,rect,_ in lines:
        clean=' '.join(line.upper().split())
        if not any(k in clean for k in keys):continue
        # Some multi-line instructions need human verification of the extent.
        next_note=min((r.y0 for s,r,_ in lines if r.y0>rect.y0+2 and abs(r.x0-rect.x0)<50 and re.match(r'^\s*\d+\.\s',s)),default=float('inf'))
        related=[s for s,r,_ in lines if s!=line and r.x0>=rect.x0-15 and r.x0<rect.x1+95 and rect.y0+6 < r.y0 <=rect.y1+45 and r.y0<next_note and re.search(r'\b(?:SURFACES|COATING|PROCESS|BASE PLATE)\b',s,re.I)]
        label=line.strip() + (' | '+' '.join(related) if related else '')
        if any(n.raw_text==label for n in found):continue
        found.append(Characteristic(0,base._reference_location(page,rect,page_i),'SEE PRINT','','','NOTE',page_i,tuple(rect),label,'VISUAL','Verify manufacturing instruction and affected surfaces','',{'source':label,'drawing_name':pdf_name,'page_part':_drawing_number(page),'review_required':True,'interpretation':'manufacturing instruction'}))
    return found

def extract_pdf_dimensions(pdf_path: str | Path) -> list[Characteristic]:
    """Main drop-in entry point for the GUI and runner.

    Keeps raw provenance and NEEDS REVIEW marks in metadata/comments. Makes no
    unsupported assertion that GD&T vectors or leader lines are fully decoded.
    """
    path=Path(pdf_path)
    raw=_legacy_extract(path)
    skipped=list(base.get_last_skipped_candidates())
    result=[]
    with fitz.open(path) as doc:
        by_page={i:[] for i in range(len(doc))}
        for c in raw:by_page[c.page_index].append(c)
        for pi,page in enumerate(doc):
            rules=parse_sheet_rules(page)
            candidates=by_page[pi]
            threads=_thread_features(page,pi,path.stem,skipped)
            gdt=_gdt_features(page,pi,path.stem)
            accepted=[]
            for c in candidates:
                rect=_c_rect(c)
                reason=region_reason(page,rect,str(c.metadata.get('source','')))
                if reason:
                    _skip(skipped,c,reason);continue
                if _thread_part(c,threads+gdt):
                    _skip(skipped,c,'part of grouped thread specification');continue
                if _is_modifier(c,candidates):
                    _skip(skipped,c,'tolerance component grouped with parent dimension');continue
                if c.type=='WELD':
                    # Symbol arrows or vector weld graphics are not fully decoded.
                    c.lsl=c.usl=''
                    c.metadata['review_required']=True
                    c.metadata['interpretation']='weld; verify symbol/leader/length/pitch'
                    c.comments=(c.comments+' | ' if c.comments else '')+'VERIFY WELD SYMBOL / LEADER / SIZE'
                else:
                    explicit=_explicit_limits(c,page)
                    if explicit:
                        c.lsl,c.usl,source,needs_review=explicit
                    else:
                        c.lsl,c.usl,source,needs_review=_default_limits(c,rules)
                    c.metadata['tolerance_source']=source
                    c.metadata['review_required']=needs_review
                    if needs_review:
                        c.comments=(c.comments+' | ' if c.comments else '')+'VERIFY TOLERANCE: '+source
                c.metadata['sheet_rules']=vars(rules)
                c.metadata['page_part']=_drawing_number(page)
                if GDTS.search(str(c.metadata.get('source',''))):
                    c.metadata['review_required']=True
                    c.comments=(c.comments+' | ' if c.comments else '')+'VERIFY GD&T FRAME/LEADER'
                accepted.append(c)
            # Group categorical thread requirement into one balloon each.
            for th in threads:
                th.metadata['page_part']=_drawing_number(page)
                th.metadata['sheet_rules']=vars(rules)
            result.extend(accepted+threads+gdt+_manufacturing_notes(page,pi,path.stem))
    for n,c in enumerate(result,1):c.char_number=n
    base.LAST_EXTRACTION_DEBUG['skipped']=skipped
    return result


def _drawing_number(page:fitz.Page)->str:
    # Set the actual sheet part when layout makes it recoverable.
    footer=page.get_text('words')
    labels=[w for w in footer if w[1]>page.rect.height*.90 and re.fullmatch(r'016858(?:-\d+)?',str(w[4]))]
    return labels[-1][4] if labels else ''


def get_last_skipped_candidates()->list[SkippedCandidate]:
    return base.get_last_skipped_candidates()

write_debug_report=base.write_debug_report
TITLE_BLOCK_DEFAULTS=base.TITLE_BLOCK_DEFAULTS
TOLERANCE_PATTERN=base.TOLERANCE_PATTERN