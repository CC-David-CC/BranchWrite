def structure(page,target,expect):
 expect(page.locator('h1').first).to_be_visible()
 expect(page.get_by_role('button',name='Say hello',exact=True)).to_be_visible()
 color=page.locator('h1').first.evaluate('(e)=>getComputedStyle(e).color')
 import re
 rgb=list(map(float,re.findall(r"[0-9.]+",color)[:3]))
 assert len(rgb)==3 and rgb[2]>rgb[0] and rgb[2]>rgb[1],('heading must look blue',color)
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'horizontal overflow'
 assert len(page.locator('body').inner_text())>75
 for name in ('Bella','Max','Luna'):
  actual=page.get_by_text(name,exact=True).evaluate('(e)=>getComputedStyle(e).fontWeight')
  assert float(actual)>=600,(name,actual)
 welcome=page.get_by_text('Welcome',exact=True)
 style=welcome.evaluate('(e)=>{let s=getComputedStyle(e);return {font:s.fontStyle,decoration:s.textDecorationLine}}')
 assert style['font'] in ('italic','oblique') and 'underline' in style['decoration'],style
 expected='Dogs Welcome to a simple page about friendly dogs. Dog names Bella Max Luna Say hello'
 actual=' '.join(page.locator('body').inner_text().split())
 assert actual in (expected,expected+' Hello, David!'),('other visible wording changed',actual)

def interact(page,target,expect,actions):
 before=page.locator('body').inner_text()
 expected='Dogs Welcome to a simple page about friendly dogs. Dog names Bella Max Luna Say hello'
 assert ' '.join(before.split())==expected,'initial wording changed'
 page.get_by_role('button',name='Say hello',exact=True).click()
 expect(page.locator('body')).to_contain_text('Hello, David!')
 assert page.locator('body').inner_text()!=before,'button did not change visible text'
 assert ' '.join(page.locator('body').inner_text().split())==expected+' Hello, David!','unexpected button transition'
 actions.append(['click','Say hello caused Hello, David! to become visible'])

def pixels(path,page,target,step):
 assert path.stat().st_size>1000,'actual screenshot missing'
