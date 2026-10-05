const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[2],'utf8');
function create(storageFails=false){
 const values={};const catalog={modules:[{lessons:[{id:'one',revision:2,quiz_path:'q',exercise_id:'e',live_required:true},{id:'two',revision:1,quiz_path:'q'}]}]};
 const w={Event:function(name){this.type=name;},dispatchEvent:()=>{},localStorage:{setItem:(k,v)=>{if(storageFails)throw Error('blocked');values[k]=v;},getItem:k=>values[k],removeItem:k=>delete values[k]}};
 const context={window:w,document:{getElementById:()=>({textContent:JSON.stringify(catalog)})},TextEncoder,Date,console};vm.runInNewContext(source,context);return w.CodexProgress;
}
const p=create();p.markRead('one',2);assert.equal(p.lessonStatus('one').complete,false);
p.recordQuiz('one',2,1,true);assert.equal(p.lessonStatus('one').complete,false);
p.recordExercise('one',2,true,'a'.repeat(64));assert.equal(p.lessonStatus('one').complete,false);
let imported={schema_version:1,course_id:'codex-cli-course-ru',lessons:{one:{revision:2,read:false,codex_run:{passed:true,completed_at:'2026-10-04T00:00:00Z'}}}};
p.importJSON(JSON.stringify(imported));assert.equal(p.lessonStatus('one').complete,true);assert(p.getState().lessons.one.quiz.passed);
const before=p.exportJSON();
const invalid=[[],{}, {schema_version:1,course_id:'other',lessons:{}},{schema_version:1,course_id:'codex-cli-course-ru',lessons:[]},{schema_version:1,course_id:'codex-cli-course-ru',lessons:{one:42}}];
for(const x of invalid){assert.throws(()=>p.importJSON(JSON.stringify(x)));assert.equal(p.exportJSON(),before);}
assert.throws(()=>p.importJSON('{"schema_version":1,"course_id":"codex-cli-course-ru","lessons":{"__proto__":{"revision":1,"read":true}}}'));
assert.throws(()=>p.importJSON('x'.repeat(1024*1024+1)));assert.equal(p.exportJSON(),before);
let old={schema_version:1,course_id:'codex-cli-course-ru',lessons:{one:{revision:1,read:true},unknown:{revision:1,read:false}}};
p.importJSON(JSON.stringify(old));assert.equal(p.lessonStatus('one').complete,true);assert(p.getState().unmapped['one@1']);p.reset();p.importJSON(JSON.stringify(old));assert.equal(p.lessonStatus('one').complete,false);assert(p.getState().lessons.one.needs_review);assert(p.getState().unmapped.unknown);
p.markRead('one',2);assert(p.getState().unmapped['one@1']);assert.equal(p.getState().lessons.one.quiz,null);
p.reset();assert.equal(Object.keys(p.getState().lessons).length,0);p.importJSON(before);assert.equal(p.lessonStatus('one').complete,true);
const blocked=create(true);blocked.markRead('two',1);assert.equal(blocked.isStorageAvailable(),false);assert(blocked.exportJSON().includes('two'));
console.log('PASS: actual progress.js completion, merge, malformed import, prototype, size, revision, export/reset/import, unavailable storage');
