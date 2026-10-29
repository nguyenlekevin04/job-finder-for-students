// The site moved from Render to Vercel. Render still serves the old address
// (dresden-student-jobs.onrender.com) and can't redirect on its free plan
// through our tooling, so the page forwards itself before first paint.
//
// Bookmarks and the theme live in localStorage, which belongs to one address.
// The old address passes them along in the URL hash; the new one imports them
// only when the visitor really came from the old address (document.referrer),
// so a crafted link can't plant bookmarks, and only https job links are kept.
// Remove this once the Render site is deleted.

export const NEW_ORIGIN = "https://dresden-jobs.vercel.app";
export const OLD_ORIGIN = "https://dresden-student-jobs.onrender.com";

export const moveScript = `(function(){
var B="dsj:bookmarks:v1",T="dsj:theme",P="#dsj-move=";
if(location.origin===${JSON.stringify(OLD_ORIGIN)}){
  var d={};
  try{d.b=localStorage.getItem(B);d.t=localStorage.getItem(T)}catch(e){}
  location.replace(${JSON.stringify(NEW_ORIGIN)}+location.pathname+location.search+P+encodeURIComponent(JSON.stringify(d)));
  return;
}
if(location.hash.indexOf(P)!==0)return;
var h=location.hash.slice(P.length);
history.replaceState(null,"",location.pathname+location.search);
if(document.referrer.indexOf(${JSON.stringify(OLD_ORIGIN + "/")})!==0)return;
try{
  var m=JSON.parse(decodeURIComponent(h));
  if(m.b){
    var cur=JSON.parse(localStorage.getItem(B)||"{}"),inc=JSON.parse(m.b);
    for(var k in inc){
      var j=inc[k];
      if(!cur[k]&&j&&j.links&&j.links.length&&j.links.every(function(l){return/^https:\\/\\//.test(l.url)}))cur[k]=j;
    }
    localStorage.setItem(B,JSON.stringify(cur));
  }
  if((m.t==="dark"||m.t==="light")&&!localStorage.getItem(T))localStorage.setItem(T,m.t);
}catch(e){}
})()`;
