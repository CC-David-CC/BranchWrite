def structure(page,target,expect):
 expect(page.get_by_role('heading').first).to_be_visible()
 text=page.locator('body').inner_text()
 assert 'Milo plays.' in text and 'Luna runs.' in text,'original task lost after restart'
 expect(page.get_by_role('button',name='Say hello',exact=True)).to_be_visible()
 assert page.locator('[src^="http"],link[href^="http"]').count()==0,'external dependencies'
def interact(page,target,expect,actions):
 page.get_by_role('button',name='Say hello',exact=True).click()
 expect(page.get_by_text('Hello, David!',exact=True)).to_be_visible()
 actions.append(['click','Say hello -> Hello, David!'])
def pixels(path,page,target,phase):
 from PIL import Image
 with Image.open(path) as image:assert image.format=='PNG'
 assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'),'horizontal overflow'
