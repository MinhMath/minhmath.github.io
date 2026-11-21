(()=>{
 const map=document.querySelector('.travel-map');
 if(!map)return;
 const svg=map.querySelector('svg');
 const pins=[...map.querySelectorAll('.travel-pin')];
 const buttons=[...map.querySelectorAll('[data-map-view]')];
 const select=map.querySelector('select');
 const caption=map.querySelector('.travel-map-caption');
 const views={world:[0,15,1000,450],europe:[455,87,130,58.5],asia:[680,106,330,148.5],vietnam:[760,181,80,36]};
 function view(name){
  const box=views[name];
  svg.setAttribute('viewBox',box.join(' '));
  buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.mapView===name)));
  pins.forEach(pin=>{
   pin.querySelector('.travel-dot').setAttribute('r',box[2]*.0032);
   pin.querySelector('.travel-hit').setAttribute('r',box[2]*.014);
   const x=Number(pin.dataset.x),y=Number(pin.dataset.y);
   pin.setAttribute('tabindex',x>=box[0]&&x<=box[0]+box[2]&&y>=box[1]&&y<=box[1]+box[3]?'0':'-1');
  });
 }
 function choose(pin,zoom){
  const x=Number(pin.dataset.x),y=Number(pin.dataset.y);
  if(zoom){
   const name=x>=455&&x<=585&&y>=87&&y<=145.5?'europe':pin.getAttribute('aria-label').includes('Vietnam')?'vietnam':x>=680&&x<=1010&&y>=106&&y<=254.5?'asia':'world';
   view(name);
  }
  pins.forEach(item=>item.classList.toggle('is-selected',item===pin));
  select.value=pin.dataset.place;
  caption.textContent=pin.getAttribute('aria-label');
 }
 buttons.forEach(button=>button.addEventListener('click',()=>view(button.dataset.mapView)));
 pins.forEach(pin=>{
  pin.addEventListener('click',()=>choose(pin,false));
  pin.addEventListener('keydown',event=>{
   if(event.key==='Enter'||event.key===' '){event.preventDefault();choose(pin,false);}
  });
 });
 select.addEventListener('change',()=>{
  const pin=pins.find(item=>item.dataset.place===select.value);
  if(pin)choose(pin,true);
 });
 view('world');
})();
