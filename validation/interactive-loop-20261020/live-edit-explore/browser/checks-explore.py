EXPECTED='green'
import re

def structure(page,target,expect):
 expect(page.locator('h1')).to_be_visible()
 assert 'bird' in page.locator('h1').inner_text().lower()
 color=page.locator('h1').evaluate('(e)=>getComputedStyle(e).color')
 rgb=list(map(float,re.findall(r'[0-9.]+',color)[:3]));r,g,b=rgb
 expected=EXPECTED
 if expected=='blue':assert b>r*1.15 and b>g*1.1,('heading is not blue',color)
 elif expected=='purple':assert r>g*1.2 and b>g*1.2 and .4<r/max(b,1)<2,('heading is not purple',color)
 elif expected=='green':assert g>r*1.15 and g>b*1.1,('heading is not green',color)
 else:raise AssertionError(expected)
 assert page.locator('[src^="http"],link[href^="http"]').count()==0,'external dependency'
 expect(page.get_by_role('button').first).to_be_visible()

def interact(page,target,expect,actions):
 button=page.get_by_role('button').first;button.click()
 assert 'feathers' in page.locator('body').inner_text().lower(),'button did not reveal original fact'
 actions.append(['click','bird button -> feathers fact'])
 actions.append(['heading-color',page.locator('h1').evaluate('(e)=>getComputedStyle(e).color')])

def pixels(path,page,target,phase):
 from PIL import Image
 with Image.open(path) as image:assert image.format=='PNG'
 assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'),'horizontal overflow'
