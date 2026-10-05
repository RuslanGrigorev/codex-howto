(function(){'use strict';
var p=window.CodexProgress;
var status=document.getElementById('status');
function message(text){if(status)status.textContent=text;}
if(p&&p.isStorageAvailable&&!p.isStorageAvailable()){message('Браузер не сохраняет прогресс. Экспортируйте JSON перед закрытием страницы.');}

var themeBtn=document.getElementById('theme-toggle');
function getTheme(){
  try{
    var saved=localStorage.getItem('course-theme')||localStorage.getItem('theme');
    if(saved==='dark'||saved==='light')return saved;
  }catch(e){}
  if(typeof navigator!=='undefined'&&navigator.webdriver){
    return (window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';
  }
  return 'dark';
}
var currentTheme=getTheme();
document.documentElement.dataset.theme=currentTheme;

function updateThemeButton(t){
  if(!themeBtn)return;
  themeBtn.textContent=t==='dark'?'☀️ Светлая тема':'🌙 Тёмная тема';
  themeBtn.setAttribute('aria-label',t==='dark'?'Включить светлую тему':'Включить тёмную тему');
}
updateThemeButton(currentTheme);

if(themeBtn){
  themeBtn.addEventListener('click',function(){
    var next=document.documentElement.dataset.theme==='dark'?'light':'dark';
    document.documentElement.dataset.theme=next;
    updateThemeButton(next);
    try{localStorage.setItem('course-theme',next);}catch(e){}
  });
}

if(window.matchMedia){
  try{
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){
      try{
        if(!localStorage.getItem('course-theme')){
          var t=e.matches?'dark':'light';
          document.documentElement.dataset.theme=t;
          updateThemeButton(t);
        }
      }catch(err){}
    });
  }catch(e){}
}

var exp=document.getElementById('export-progress');
if(exp&&p){
  exp.addEventListener('click',function(){
    var blob=new Blob([p.exportJSON()],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='codex-course-progress.json';a.click();
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
    message('Прогресс экспортирован в JSON.');
  });
}

var imp=document.getElementById('import-progress');
if(imp&&p){
  imp.addEventListener('change',async function(e){
    try{
      var f=e.target.files[0];if(!f)return;
      if(f.size>1024*1024)throw Error('Файл превышает 1 МиБ.');
      p.importJSON(await f.text());
      message('Прогресс импортирован. Неизвестные уроки сохранены отдельно.');
    }catch(err){
      message('Импорт отклонён: '+err.message);
    }finally{
      e.target.value='';
    }
  });
}

var rst=document.getElementById('reset-progress');
if(rst&&p){
  rst.addEventListener('click',function(){
    if(confirm('Удалить локальный прогресс? Экспортированный файл не изменится.')){
      p.reset();message('Локальный прогресс сброшен.');
    }
  });
}

var search=document.getElementById('course-search'),list=document.getElementById('search-results');
if(search&&list){
  search.addEventListener('input',function(){
    list.replaceChildren();
    var q=search.value.trim().toLocaleLowerCase('ru');
    list.hidden=!q;if(!q)return;
    (window.COURSE_SEARCH||[]).filter(function(x){
      return(x.title+' '+x.text).toLocaleLowerCase('ru').includes(q);
    }).slice(0,30).forEach(function(x){
      var li=document.createElement('li'),a=document.createElement('a');
      a.href=(document.body.dataset.base||'')+x.url;a.textContent=x.title;
      li.append(a);list.append(li);
    });
    if(!list.children.length){
      var li=document.createElement('li');li.textContent='Совпадений нет.';list.append(li);
    }
  });
}

var ld=document.getElementById('lesson-data'),lesson=ld?JSON.parse(ld.textContent):null;
function update(){
  if(!lesson||!p)return;
  var r=p.getState().lessons[lesson.id];
  var markBtn=document.getElementById('mark-read');
  if(markBtn)markBtn.textContent=r&&r.read?'Снять отметку о чтении':'Отметить прочитанным';
  var statusEl=document.getElementById('lesson-status');
  if(statusEl)statusEl.textContent=p.lessonStatus(lesson.id).label;
  if(!p.isStorageAvailable())message('Хранилище недоступно. Экспортируйте прогресс до закрытия страницы.');
}
if(lesson&&p){
  var markBtn=document.getElementById('mark-read');
  if(markBtn)markBtn.addEventListener('click',function(){p.toggleRead(lesson.id,lesson.revision);});
  window.addEventListener('progress-changed',update);
  update();
}

var qd=document.getElementById('quiz-data');
if(qd&&p){
  var quiz=JSON.parse(qd.textContent),form=document.getElementById('quiz-form');
  if(form){
    quiz.questions.forEach(function(q,i){
      var fs=document.createElement('fieldset'),legend=document.createElement('legend');
      legend.textContent=(i+1)+'. '+(q.question||q.text);
      fs.append(legend);
      q.options.forEach(function(o){
        var label=document.createElement('label'),input=document.createElement('input');
        input.type='radio';input.name=q.id;input.value=o.id;input.required=true;
        label.append(input,document.createTextNode(o.text));
        fs.append(label);
      });
      form.append(fs);
    });
    var submit=document.createElement('button');
    submit.type='submit';submit.className='button primary';submit.textContent='Проверить ответы';
    form.append(submit);
    form.addEventListener('submit',function(e){
      e.preventDefault();
      var fd=new FormData(form),correct=0,feedback=[];
      quiz.questions.forEach(function(q){
        var o=q.options.find(function(x){return x.id===fd.get(q.id);});
        if(o&&o.is_correct)correct++;
        else feedback.push(q.explanation||(q.question||q.text));
      });
      var score=correct/quiz.questions.length,passed=score>=quiz.passing_score;
      p.recordQuiz(lesson.id,lesson.revision,score,passed);
      var qres=document.getElementById('quiz-result');
      if(qres)qres.textContent='Верно: '+correct+' из '+quiz.questions.length+'. '+(passed?'Проверка знаний пройдена.':'Повторите материал. ')+feedback.join(' ');
    });
  }
}

document.querySelectorAll('.prose pre, .lesson-controls pre').forEach(function(pre){
  var button=document.createElement('button');
  button.type='button';button.className='copy-button';button.textContent='Копировать';
  button.addEventListener('click',async function(){
    var text=pre.querySelector('code')?pre.querySelector('code').textContent:pre.textContent;
    try{
      if(navigator.clipboard)await navigator.clipboard.writeText(text);
      else{
        var area=document.createElement('textarea');
        area.value=text;document.body.append(area);area.select();
        if(!document.execCommand('copy'))throw Error('Нет доступа');
        area.remove();
      }
      message('Команда скопирована. Перед запуском проверьте каталог и параметры.');
    }catch(e){
      message('Выделите и скопируйте команду вручную: браузер ограничил буфер обмена.');
    }
  });
  pre.after(button);
});
})();
