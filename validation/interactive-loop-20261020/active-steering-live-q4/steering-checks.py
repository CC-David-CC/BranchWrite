import json
STYLES = """terms => {
 const out = {};
 for (const word of terms) {
  const matches=[];
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  let node;
  while(node=walker.nextNode()) {
   const el=node.parentElement;
   if(!el || el.closest('script,style,template,noscript') || !el.getClientRects().length) continue;
   if(!node.textContent.toLowerCase().split(/\W+/).includes(word.toLowerCase())) continue;
   const cs=getComputedStyle(el);let underline=false;
   for(let p=el;p;p=p.parentElement) if(getComputedStyle(p).textDecorationLine.split(' ').includes('underline')) underline=true;
   matches.push({weight:cs.fontWeight,style:cs.fontStyle,underline});
  }
  out[word]=matches;
 }
 return out;
}"""
NAMES=['Rex','Luna','Milo']
VERBS=['runs','jumps','plays']
def values(page): return page.evaluate(STYLES,NAMES+VERBS)
def structure(page,target,expect):
    data=values(page)
    assert 'meet our dogs' in page.locator('body').inner_text().lower(), 'Original requested section is missing'
    for word in NAMES:
        assert data[word], 'Missing dog name: '+word
        assert all(float(row['weight'])>=700 for row in data[word]), 'Name is not bold: '+word+' '+json.dumps(data[word])
    for word in VERBS:
        assert data[word], 'Missing action word: '+word
        assert all(row['style'].startswith(('italic','oblique')) and row['underline'] for row in data[word]), 'Verb must be italic and underlined: '+word+' '+json.dumps(data[word])
    expect(page.get_by_role('heading',name='Dogs are wonderful.',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Say hello',exact=True)).to_be_visible()
def interact(page,target,expect,actions):
    for word,rows in values(page).items():
        actions.append(['computed:'+word,json.dumps(rows,separators=(',',':'))[:256]])
    page.get_by_role('button',name='Say hello',exact=True).click()
    expect(page.get_by_text('Hello, David!',exact=True)).to_be_visible()
    actions.append(['click','Say hello -> Hello, David!'])
    page.get_by_role('heading',name='Meet our dogs',exact=True).scroll_into_view_if_needed()
    actions.append(['scroll','Meet our dogs'])
def pixels(path,page,target,phase):
    from PIL import Image
    with Image.open(path) as image: assert image.format=='PNG'
    assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'), 'Page exceeds the viewport width'
