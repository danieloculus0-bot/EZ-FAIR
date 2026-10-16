"""Regression tests anchored to actual Husky 016858 Rev D example."""
from __future__ import annotations

from pathlib import Path
import fitz
import pytest

from engineering_characteristics import (extract_pdf_dimensions, parse_sheet_rules,
                                          region_reason, _explicit_limits)
from extractor_engine import Characteristic

FIXTURE=Path(__file__).parent.parent/'fixtures'/'016858_REV_D_NDM_3-5-25_BALLOONED.pdf'


def test_title_block_tolerance_table():
    doc=fitz.open()
    page=doc.new_page(width=1224,height=792)
    for x,y,line in [(839,685,'TOLERANCES'),(844,704,'X/Y'),(870,704,'1/64'),(844,717,'.XX'),(870,717,'.010'),(839,730,'.XXX'),(870,730,'.005'),(870,743,'.5')]:
        page.insert_text((x,y),line,fontsize=8)
    rules=parse_sheet_rules(page)
    assert rules.two==pytest.approx(.010)
    assert rules.three==pytest.approx(.005)
    assert rules.fraction==pytest.approx(1/64)
    assert rules.angular==pytest.approx(.5)


def test_region_classification():
    doc=fitz.open();page=doc.new_page(width=1224,height=792)
    assert region_reason(page,fitz.Rect(1100,500,1140,516),'Issued Date: 3/6/25')
    assert region_reason(page,fitz.Rect(150,742,200,760),'20.290 WAS 20.000')
    assert region_reason(page,fitz.Rect(1050,330,1070,346),'SCALE 0.250')
    assert region_reason(page,fitz.Rect(705,346,768,371),'11.990+.005') is None
    assert region_reason(page,fitz.Rect(960,352,990,370),'3.504 .003') is None


def test_limits_provisional_when_plus_minus_glyph_absent():
    doc=fitz.open();page=doc.new_page(width=1224,height=792)
    page.insert_text((705,370),'11.990+.005',fontsize=12)
    page.insert_text((735,381),'-.015',fontsize=12)
    page.insert_text((960,370),'3.504 .003',fontsize=12)
    g=Characteristic(1,'P1',11.990,0,0,'LINEAR',0,(705,355,780,371),'11.990',metadata={'source':'11.990+.005'})
    h=Characteristic(2,'P1',3.504,0,0,'LINEAR',0,(960,355,990,371),'3.504',metadata={'source':'3.504 .003'})
    gl=_explicit_limits(g,page)
    assert gl is not None and gl[:2]==(11.975,11.995)
    hl=_explicit_limits(h,page)
    assert hl is not None and hl[:2]==(3.501,3.507) and hl[3] is True


def test_husky_actual_pdf_regression():
    if not FIXTURE.exists():pytest.skip('Customer proprietary drawing intentionally not checked into git')
    doc=fitz.open(FIXTURE)
    assert len(doc)==11
    sheet5=parse_sheet_rules(doc[4]); assert sheet5.two==.01 and sheet5.three==.005
    chars=extract_pdf_dimensions(FIXTURE)
    assert len(chars) >= 55
    g=[c for c in chars if c.page_index==4 and c.raw_text.strip()=='11.990']
    assert len(g)==1 and (g[0].lsl,g[0].usl)==(11.975,11.995)
    h=[c for c in chars if c.page_index==4 and c.raw_text.strip()=='3.504']
    assert len(h)==1 and (h[0].lsl,h[0].usl)==(3.501,3.507)
    assert h[0].metadata['review_required'] is True
    assert not [c for c in chars if c.page_index==4 and c.raw_text.strip() in ('.005','.015','.003')]
    assert not [c for c in chars if 'SCALE' in str(c.metadata.get('source','')).upper()]
    assert not [c for c in chars if 'WAS ' in str(c.metadata.get('source','')).upper()]
    assert not [c for c in chars if c.page_index==0 and c.raw_text in ('.375', '.75') and c.rect[0]>900]
    assert len([c for c in chars if c.page_index==4 and c.type=='THREAD'])>=2
    assert len([c for c in chars if c.page_index==4 and c.type=='NOTE'])>=2
    assert len([c for c in chars if c.page_index==0 and c.type=='WELD' and '1-2.7' in c.raw_text])==1
    assert all(c.lsl=='' and c.usl=='' for c in chars if c.page_index==0 and c.raw_text=='3/16')
    assert len(set(c.metadata.get('page_part','') for c in chars))>2
    assert all(c.char_number==i for i,c in enumerate(chars,1))


def test_readable_gdt_stays_one_categorical_requirement():
    from engineering_characteristics import _gdt_features
    doc=fitz.open();page=doc.new_page(width=1224,height=792)
    page.insert_text((250,220),'POSITION ⌖ 0.005 A B C',fontsize=10)
    features=_gdt_features(page,0,'fixture')
    assert len(features)==1 and features[0].type=='GD&T'
    assert features[0].lsl=='' and features[0].metadata['review_required']