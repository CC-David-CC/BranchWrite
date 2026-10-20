def structure(page,target,expect):
 expect(page.get_by_role('heading').first).to_be_visible()
 expect(page.locator('body')).to_contain_text('Milo plays.')
 expect(page.locator('body')).to_contain_text('Luna runs.')
 expect(page.get_by_role('button',name='Say hello',exact=True)).to_be_visible()
 assert page.locator('[src^="http"],link[href^="http"]').count()==0,'external dependency'
def interact(page,target,expect,actions):
 page.get_by_role('button',name='Say hello',exact=True).click()
 expect(page.get_by_text('Hello, David!',exact=True)).to_be_visible()
 actions.append(['click','Say hello -> Hello, David!'])
def pixels(path,page,target,phase):
 assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'),'horizontal overflow'
