/* Один локальный формат результатов. Импорт не является защищённым сертификатом. */
(function(global){'use strict';
var STORAGE_KEY='codex-cli-course-ru.progress.v1', COURSE_ID='codex-cli-course-ru', LIMIT=1024*1024;
var catalog={},available=true;
try{var node=document.getElementById('course-data');var c=node?JSON.parse(node.textContent):{modules:[]};c.modules.forEach(function(m){m.lessons.forEach(function(l){catalog[l.id]=l;});});}catch(e){}
function empty(){return {schema_version:1,course_id:COURSE_ID,course_version:'0.3.0',lessons:{},unmapped:{}};}
var state=empty();
function obj(x){return x!==null&&typeof x==='object'&&!Array.isArray(x);}
function goodID(k){return /^[a-z0-9][a-z0-9.@-]*$/.test(k)&&!['__proto__','prototype','constructor'].includes(k);}
function result(x,kind){if(x===null)return true;if(!obj(x)||typeof x.passed!=='boolean'||typeof x.completed_at!=='string'||!Number.isFinite(Date.parse(x.completed_at)))return false;if(kind==='quiz'&&(!Number.isFinite(x.score)||x.score<0||x.score>1))return false;if(kind==='exercise'&&x.execution_hash!==undefined&&!/^[a-f0-9]{64}$/.test(x.execution_hash))return false;return true;}
function record(x){return obj(x)&&Number.isInteger(x.revision)&&x.revision>0&&typeof x.read==='boolean'&&(x.needs_review===undefined||typeof x.needs_review==='boolean')&&result(x.quiz===undefined?null:x.quiz,'quiz')&&result(x.exercise===undefined?null:x.exercise,'exercise')&&result(x.codex_run===undefined?null:x.codex_run,'codex');}
function validate(x){if(!obj(x)||x.schema_version!==1||x.course_id!==COURSE_ID||!obj(x.lessons)||(x.unmapped!==undefined&&!obj(x.unmapped)))throw Error('Несовместимый или повреждённый формат прогресса.');[x.lessons,x.unmapped||{}].forEach(function(m){Object.keys(m).forEach(function(k){if(!goodID(k)||!record(m[k]))throw Error('Некорректная запись урока: '+k);});});return x;}
function clone(x){return JSON.parse(JSON.stringify(x));}
function migrate(x){var out=clone(validate(x));out.unmapped=out.unmapped||{};Object.keys(out.lessons).forEach(function(k){var l=catalog[k];if(!l){out.unmapped[k]=out.lessons[k];delete out.lessons[k];}else{out.lessons[k].needs_review=out.lessons[k].revision!==l.revision||out.lessons[k].needs_review===true;}});return out;}
function signal(){if(typeof global.dispatchEvent==='function'&&typeof global.Event==='function')global.dispatchEvent(new global.Event('progress-changed'));}
function save(){try{if(available)global.localStorage.setItem(STORAGE_KEY,JSON.stringify(state));}catch(e){available=false;}signal();return available;}
try{var store=global.localStorage;store.setItem('__course_probe__','1');store.removeItem('__course_probe__');var raw=store.getItem(STORAGE_KEY);if(raw)state=migrate(JSON.parse(raw));}catch(e){available=false;}
function ensure(id,revision){if(!catalog[id]||catalog[id].revision!==revision)throw Error('Неизвестный урок или редакция.');var r=state.lessons[id];if(!r||r.revision!==revision||r.needs_review){if(r)state.unmapped[id+'@'+r.revision]=clone(r);r={revision:revision,read:false,quiz:null,exercise:null,codex_run:null,needs_review:false};state.lessons[id]=r;}return r;}
function setRead(id,v,revision){if(typeof v!=='boolean')throw Error('Ожидалось логическое значение');var r=ensure(id,revision);r.read=v;save();return clone(r);}
function status(id){var l=catalog[id],r=state.lessons[id];if(!l||!r)return {complete:false,label:'Не начат'};if(r.needs_review||r.revision!==l.revision)return {complete:false,label:'Требуется повторная проверка'};var complete=r.read&&(!l.quiz_path||(r.quiz&&r.quiz.passed))&&(!l.exercise_id||(r.exercise&&r.exercise.passed))&&(!l.live_required||(r.codex_run&&r.codex_run.passed));return {complete:!!complete,label:complete?'Завершён':r.read?'Прочитан · проверки отдельно':'В работе'};}
function importJSON(text){if(typeof text!=='string'||new TextEncoder().encode(text).length>LIMIT)throw Error('Файл превышает 1 МиБ.');var incoming=migrate(JSON.parse(text));var next=clone(state);Object.keys(incoming.unmapped).forEach(function(k){next.unmapped[k]=incoming.unmapped[k];});Object.keys(incoming.lessons).forEach(function(k){var r=incoming.lessons[k],old=next.lessons[k];if(old&&old.revision!==r.revision){if(old.revision===catalog[k].revision&&!old.needs_review){next.unmapped[k+'@'+r.revision]=r;return;}next.unmapped[k+'@'+old.revision]=old;}if(old&&old.revision===r.revision){r.read=r.read||old.read;['quiz','exercise','codex_run'].forEach(function(f){if(!r[f]||(old[f]&&Date.parse(old[f].completed_at)>Date.parse(r[f].completed_at)))r[f]=old[f]||null;});r.needs_review=r.needs_review||old.needs_review;}next.lessons[k]=r;});validate(next);state=next;save();return clone(state);}
global.CodexProgress={
 getState:function(){return clone(state);},validate:validate,migrate:migrate,isStorageAvailable:function(){return available;},lessonStatus:status,
 setRead:setRead,markRead:function(id,rev){return setRead(id,true,rev);},toggleRead:function(id,rev){return setRead(id,!(state.lessons[id]&&state.lessons[id].read),rev);},
 recordQuiz:function(id,rev,score,passed){if(!Number.isFinite(score)||score<0||score>1||typeof passed!=='boolean')throw Error('Некорректный результат квиза');var r=ensure(id,rev);r.quiz={score:score,passed:passed,completed_at:new Date().toISOString()};save();return clone(r);},
 recordExercise:function(id,rev,passed,hash){if(typeof passed!=='boolean'||!/^[a-f0-9]{64}$/.test(hash))throw Error('Некорректное доказательство упражнения');var r=ensure(id,rev);r.exercise={passed:passed,execution_hash:hash,completed_at:new Date().toISOString()};save();return clone(r);},
 exportJSON:function(){return JSON.stringify(state,null,2);},importJSON:importJSON,
 reset:function(){state=empty();save();return clone(state);}
};
})(typeof window!=='undefined'?window:globalThis);
