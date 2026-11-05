// Synthetic larger dungeons: N rooms, varied names/descriptions, realistic exits.
import fs from 'node:fs';
const adj=['Damp','Ruined','Silent','Gilded','Collapsed','Flooded','Smoky','Narrow','Vast','Forgotten','Crumbling','Moss-covered'];
const noun=['Hall','Vault','Crypt','Passage','Chapel','Armory','Den','Cistern','Gallery','Barracks','Shrine','Pantry'];
const desc=['Cobwebs hang from every beam.','A cold draft whistles through cracks in the wall.','Rusted chains dangle from the ceiling.','The floor is slick with algae.','Scorch marks blacken the stone.','A faint chanting echoes from somewhere below.','Broken pottery crunches underfoot.','Rat droppings and gnawed bones are everywhere.'];
const sizes=['small','medium','large'],terr=['stone_floor','dirt','water'],light=['dark','dim','bright'],types=['archway','wooden','secret'],states=['open','closed','locked'],dirs=['n','e','s','w','ne','nw','se','sw'];
let seed=42;const r=n=>{seed=(seed*1103515245+12345)&0x7fffffff;return seed%n};
export function gen(N){let s=`name: "Synthetic ${N}"\nlevel: 3\ntheme: "crypt"\nrooms:\n`;
for(let i=0;i<N;i++){s+=`  - id: room_${i}\n    name: "${adj[r(12)]} ${noun[r(12)]}"\n    description: "${desc[r(8)]} ${desc[r(8)]}"\n    size: ${sizes[r(3)]}\n    terrain: ${terr[r(3)]}\n    light: ${light[r(3)]}\n`;
 if(i===0)s+=`    entrance: true\n`;s+=`    exits:\n`;
 const ex=[];if(i>0)ex.push(i-1);if(i<N-1)ex.push(i+1);if(r(3)===0&&N>3)ex.push(r(N));
 for(const t of ex){const st=states[r(3)];s+=`      - target: room_${t}\n        direction: ${dirs[r(8)]}\n        type: ${types[r(3)]}\n        state: ${st}\n`;if(st!=='open')s+=`        dc: ${8+r(10)}\n`;}
 s+='\n';}return s;}
if(process.argv[2]){for(const n of [10,25,50,100,200]) fs.writeFileSync(`synth_${n}.yaml`,gen(n));}
