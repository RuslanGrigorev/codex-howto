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
      var detailedBox=document.getElementById('quiz-detailed-feedback');
      if(detailedBox){detailedBox.replaceChildren();detailedBox.hidden=false;}
      quiz.questions.forEach(function(q,idx){
        var selectedId=fd.get(q.id);
        var o=q.options.find(function(x){return x.id===selectedId;});
        var correctOption=q.options.find(function(x){return x.is_correct;});
        var isOk=o&&o.is_correct;
        if(isOk)correct++;
        else feedback.push(q.explanation||(q.question||q.text));
        if(detailedBox){
          var item=document.createElement('div');
          item.className='quiz-feedback-item '+(isOk?'correct':'incorrect');
          var header=document.createElement('div');
          header.className='quiz-feedback-header';
          var titleSpan=document.createElement('span');
          titleSpan.textContent='Вопрос '+(idx+1)+': '+(isOk?'Верно':'Неверно');
          var badge=document.createElement('span');
          badge.className='quiz-badge '+(isOk?'correct':'incorrect');
          badge.textContent=isOk?'✓ Верно':'✗ Ошибка';
          header.append(titleSpan,badge);
          var qText=document.createElement('div');
          qText.style.fontWeight='500';
          qText.textContent=q.question||q.text;
          var exp=document.createElement('div');
          exp.className='quiz-explanation-text';
          var detailMsg = '';
          if (isOk) {
            detailMsg = (o && o.rationale) ? o.rationale : (q.explanation || 'Ответ верен.');
          } else {
            var optRationale = o ? (o.rationale || o.misconception) : null;
            var prefix = optRationale ? ('Разбор выбранного ответа: ' + optRationale + ' ') : '';
            var correctText = correctOption ? correctOption.text : '';
            detailMsg = prefix + 'Правильный ответ: ' + correctText + (q.explanation ? (' — ' + q.explanation) : '');
          }
          exp.textContent = detailMsg;
          item.append(header,qText,exp);
          detailedBox.append(item);
        }
      });
      var score=correct/quiz.questions.length,passed=score>=quiz.passing_score;
      p.recordQuiz(lesson.id,lesson.revision,score,passed);
      var qres=document.getElementById('quiz-result');
      if(qres)qres.textContent='Верно: '+correct+' из '+quiz.questions.length+'. '+(passed?'Проверка знаний пройдена.':'Повторите материал. ');
    });
  }
}

// Interactive offline CLI simulator
(function initCliSimulator(){
  var widget = document.querySelector('.cli-simulator-widget');
  if(!widget)return;
  var moduleKey = widget.getAttribute('data-module') || 'start';
  var presetContainer = document.getElementById('sim-presets');
  var form = document.getElementById('sim-terminal-form');
  var input = document.getElementById('sim-input');
  var output = document.getElementById('sim-terminal-output');
  var clearBtn = document.getElementById('sim-clear');
  if(!form || !input || !output)return;

  var PRESETS = {
    'start': ['codex --help', 'codex --version', 'codex'],
    'workflow': ['/goal', '/goal pause', '/goal resume', 'codex "исправь опечатку"'],
    'safety': ['/permissions', '/status', 'codex --sandbox read-only'],
    'instructions': ['cat AGENTS.md', 'codex --model gpt-5', '/model'],
    'sessions': ['/resume', 'codex --continue'],
    'skills': ['$learn', '/skills', 'codex $project-map'],
    'mcp': ['/mcp', 'codex --mcp-config mcp.json'],
    'automation': ['codex exec "проверь код"', 'codex exec --json "status"', 'codex app-server'],
    'extensions': ['/plugins', '/hooks', 'codex --agent explorer'],
    'capstone': ['codex exec --sandbox workspace-write "комплексный аудит"', 'python scripts/verify.py --profile offline']
  };

  var commands = PRESETS[moduleKey] || PRESETS['start'];
  if(presetContainer){
    commands.forEach(function(cmd){
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'preset-btn';
      btn.textContent = cmd;
      btn.addEventListener('click', function(){
        input.value = cmd;
        executeSim(cmd);
      });
      presetContainer.append(btn);
    });
  }

  function appendLine(text, className){
    var line = document.createElement('div');
    line.className = 'terminal-line ' + (className || 'terminal-out-line');
    line.textContent = text;
    output.append(line);
    output.scrollTop = output.scrollHeight;
  }

  function executeSim(rawCmd){
    var cmd = (rawCmd || '').trim();
    if(!cmd)return;
    appendLine('user@codex-lab:~$ ' + cmd, 'user-cmd-line');

    var lower = cmd.toLowerCase();
    if(lower === 'clear'){
      output.replaceChildren();
      appendLine('[СИМУЛЯТОР CODEX CLI 0.160.0 ОЧИЩЕН]', 'system-line');
      return;
    }
    if(lower === 'help' || lower === '/help'){
      appendLine('[СИМУЛЯЦИЯ] Доступные команды симулятора Codex CLI 0.160.0:\n' +
        '  codex [ПАРАМЕТРЫ] [ПРОМПТ]\n' +
        '    --model <gpt-5 | gpt-4.1 | o3-mini>\n' +
        '    --sandbox <read-only | workspace-write | danger-full-access>\n' +
        '    --ask-for-approval <untrusted | always | never>\n' +
        '    --continue, --help, --version, exec, app-server\n' +
        '  Slash-команды сессии:\n' +
        '    /goal [/goal pause | /goal resume | /goal clear]\n' +
        '    /model [/model <название>]\n' +
        '    /permissions, /sandbox [read-only | workspace-write]\n' +
        '    /status, /skills, /mcp, /plugins, /hooks, /resume [<id>], /exit\n' +
        '  Навыки и проектные команды:\n' +
        '    $learn, cat AGENTS.md, clear');
      return;
    }
    if(lower === 'codex --version' || lower === 'codex -v' || lower === 'codex -V' || lower === '/version'){
      appendLine('codex 0.160.0 (offline docs baseline rust-v0.160.0)');
      return;
    }
    if(lower === 'codex --help' || lower === 'codex -h'){
      appendLine(
        'Codex CLI v0.160.0 (rust-v0.160.0)\n\n' +
        'Использование: codex [ПАРАМЕТРЫ] [КОМАНДА] [ПРОМПТ]\n\n' +
        'Подкоманды:\n' +
        '  exec         Неинтерактивное пакетное выполнение промпта\n' +
        '  app-server   Запуск stdio JSON-RPC 2.0 сервера интеграции\n\n' +
        'Параметры:\n' +
        '  -m, --model <МОДЕЛЬ>         Целевая модель (gpt-5, gpt-4.1)\n' +
        '  -s, --sandbox <РЕЖИМ>        Режим: read-only | workspace-write | danger-full-access\n' +
        '  --ask-for-approval <РЕЖИМ>   Запрос подтверждения: untrusted | always | never\n' +
        '  --cd <КАТАЛОГ>               Рабочий каталог\n' +
        '  --mcp-config <ФАЙЛ>          Путь к конфигурации MCP\n' +
        '  --continue, --resume         Возобновление сессии\n' +
        '  -h, --help                   Справка\n' +
        '  -V, --version                Версия'
      );
      return;
    }
    if(lower.startsWith('codex exec')){
      appendLine('[СИМУЛЯЦИЯ exec] Неинтерактивное выполнение:\n' +
        '{"type":"session.start","version":"0.160.0","mode":"exec"}\n' +
        '{"type":"item.create","item":{"type":"message","role":"user","content":"' + cmd.replace(/codex\s+exec/i, '').trim() + '"}}\n' +
        '{"type":"agent.response","status":"completed","exit_code":0}\n' +
        'Завершено с кодом 0 (успешно).');
      return;
    }
    if(lower === 'codex app-server'){
      appendLine('[СИМУЛЯЦИЯ app-server] Сервер JSON-RPC 2.0 ожидает входящие запросы в stdin.');
      return;
    }
    if(lower === 'codex' || lower.startsWith('codex ') || lower.startsWith('codex"')){
      var isReadOnly = lower.includes('read-only') || lower.includes('-s read-only') || lower.includes('--sandbox read-only');
      var isDanger = lower.includes('danger-full-access');
      var sbMode = isReadOnly ? 'read-only (только чтение: запись файлов заблокирована)' : (isDanger ? 'danger-full-access (полный доступ)' : 'workspace-write');

      var mMatch = cmd.match(/(?:--model|-m)\s+([^\s]+)/i);
      var curModel = mMatch ? mMatch[1] : 'gpt-5';

      var appMatch = cmd.match(/--ask-for-approval\s+([^\s]+)/i);
      var curApp = appMatch ? appMatch[1] : 'untrusted';

      var agentMatch = cmd.match(/--agent\s+([^\s]+)/i);
      var skillMatch = cmd.match(/\$([a-zA-Z0-9_-]+)/);

      var infoLines = [
        '[СИМУЛЯЦИЯ] Интерактивная сессия Codex CLI 0.160.0 запущена.',
        '  Рабочий каталог: /workspace',
        '  Модель: ' + curModel,
        '  Песочница: ' + sbMode,
        '  Подтверждения: ' + curApp,
        '  Сеть: disabled (автономный режим)'
      ];
      if(agentMatch){
        infoLines.push('  Субагент: ' + agentMatch[1] + ' (ролевой профиль активен)');
      }
      if(skillMatch){
        infoLines.push('  Навык: $' + skillMatch[1] + ' (инструкции навыка загружены в контекст)');
      }
      if(lower.includes('--continue') || lower.includes('--resume')){
        infoLines.push('  Возобновление: последняя активная сессия восстановлена');
      }
      if(lower.includes('--mcp-config')){
        infoLines.push('  MCP: конфигурация загружена');
      }
      infoLines.push('Введите задачу или команду (/goal, /model, /permissions, /status). Для выхода: /exit');
      appendLine(infoLines.join('\n'));
      return;
    }
    if(lower === '/model'){
      appendLine('[СИМУЛЯЦИЯ /model] Текущая модель сессии: gpt-5 (OpenAI)\n' +
        'Доступные профили моделей (0.160.0):\n' +
        '  1. gpt-5 (по умолчанию: reasoning + coding)\n' +
        '  2. gpt-4.1 (быстрая кодогенерация и рефакторинг)\n' +
        '  3. o3-mini (структурированный анализ и валидация)\n' +
        'Для переключения модели используйте: /model <название>');
      return;
    }
    if(lower.startsWith('/model ')){
      var targetModel = cmd.slice(7).trim();
      appendLine('[СИМУЛЯЦИЯ /model] Модель сессии успешно переключена на "' + targetModel + '". Контекст сохранён.');
      return;
    }
    if(lower === '/goal'){
      appendLine('[СИМУЛЯЦИЯ /goal] Текущая цель:\n' +
        '  1. [DONE] Исследование архитектуры и требований\n' +
        '  2. [IN_PROGRESS] Реализация и подготовка материалов\n' +
        '  3. [PENDING] Автономная верификация и сдача\n' +
        'Статус: АКТИВНА. Для паузы используйте: /goal pause');
      return;
    }
    if(lower === '/goal pause'){
      appendLine('[СИМУЛЯЦИЯ /goal] Долгосрочная цель приостановлена. Прогресс сохранён.');
      return;
    }
    if(lower === '/goal resume'){
      appendLine('[СИМУЛЯЦИЯ /goal] Выполнение цели возобновлено с текущего шага.');
      return;
    }
    if(lower === '/goal clear'){
      appendLine('[СИМУЛЯЦИЯ /goal] Текущая цель очищена.');
      return;
    }
    if(lower === '/permissions'){
      appendLine('[СИМУЛЯЦИЯ /permissions] Права безопасности сессии:\n' +
        '  - sandbox: workspace-write (изменение только в рабочей области)\n' +
        '  - network: blocked (автономный офлайн-режим)\n' +
        '  - approvals: untrusted (запрос подтверждения на внешние действия)');
      return;
    }
    if(lower === '/sandbox' || lower === '/sandbox read-only' || lower === 'read-only' || lower === 'рид онли' || lower === 'read only'){
      appendLine('[СИМУЛЯЦИЯ: ПЕСОЧНИЦА] Режим песочницы: read-only (только чтение).\n' +
        'Все изменения файлов и деструктивные операции заблокированы. Агент работает исключительно в режиме анализа.');
      return;
    }
    if(lower.startsWith('/sandbox ')){
      var sMode = cmd.slice(9).trim();
      appendLine('[СИМУЛЯЦИЯ /sandbox] Режим песочницы установлен в "' + sMode + '".');
      return;
    }
    if(lower === 'exit' || lower === '/exit'){
      appendLine('[СИМУЛЯЦИЯ] Сессия Codex CLI завершена. Состояние сессии сохранено в .codex/sessions.');
      return;
    }
    if(lower === '/status'){
      appendLine('[СИМУЛЯЦИЯ /status]\n' +
        '  Сессия: active (id: sess-0160-mock)\n' +
        '  Модель: baseline-0.160.0\n' +
        '  Контекст: 2,450 / 128,000 токенов (1.9%)\n' +
        '  Режим: автономный офлайн');
      return;
    }
    if(lower.startsWith('$learn')){
      appendLine('[СИМУЛЯЦИЯ $learn] Навык наставника курса активен. ' +
        'Учебный контекст загружен. Задайте вопрос или запросите подсказку.');
      return;
    }
    if(lower === '/skills'){
      appendLine('[СИМУЛЯЦИЯ /skills] Зарегистрированные навыки проекта:\n' +
        '  - $learn: автономный наставник курса Codex CLI\n' +
        '  - $project-map: построение карты проекта\n' +
        '  - $diff-review: аудит изменений');
      return;
    }
    if(lower === '/mcp'){
      appendLine('[СИМУЛЯЦИЯ /mcp] Протокол Model Context Protocol (0.160.0):\n' +
        '  Подключение: stdio / SSE\n' +
        '  Конфигурация: mcp_config.json\n' +
        '  Доступных инструментов: 0');
      return;
    }
    if(lower === '/plugins' || lower === '/hooks'){
      appendLine('[СИМУЛЯЦИЯ] Зарегистрированные хуки: PreToolUse, PostToolUse, UserPromptSubmit, Stop.');
      return;
    }
    if(lower === '/resume'){
      appendLine('[СИМУЛЯЦИЯ /resume] Сохранённые сессии в .codex/sessions:\n' +
        '  1. sess-2026-10-05-01 (активна)\n' +
        '  2. sess-2026-10-04-02 (завершена)\n' +
        'Для продолжения сессии используйте: /resume <id>');
      return;
    }
    if(lower.startsWith('/resume ')){
      var targetSess = cmd.slice(8).trim();
      appendLine('[СИМУЛЯЦИЯ /resume] Сессия "' + targetSess + '" успешно восстановлена.');
      return;
    }
    if(lower === 'cat agents.md'){
      appendLine('# Инструкции проекта (AGENTS.md)\n' +
        '- Автономный практикум Codex CLI.\n' +
        '- Кодировка UTF-8.\n' +
        '- Строгая проверка контракта без сетевых вызовов.');
      return;
    }
    if(lower.includes('verify.py')){
      appendLine('[СИМУЛЯЦИЯ verify.py] CHK-CATALOG: PASS | CHK-SITE: PASS | CHK-SITE-LINKS: PASS | CHK-BROWSER: PASS\nИтог: автономный профиль проверен.');
      return;
    }
    appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестная команда или опция "' + cmd + '". В Codex CLI 0.160.0 используйте /help для списка поддерживаемых команд (/goal, /status, /permissions, /model, /skills, /mcp, /plugins, /hooks, /resume, $learn).', 'error-line');
  }

  form.addEventListener('submit', function(e){
    e.preventDefault();
    var val = input.value;
    input.value = '';
    executeSim(val);
  });

  if(clearBtn){
    clearBtn.addEventListener('click', function(){
      output.replaceChildren();
      appendLine('[СИМУЛЯТОР CODEX CLI 0.160.0 ОЧИЩЕН]', 'system-line');
    });
  }
})();

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

document.querySelectorAll('.back-to-top, .footer-top').forEach(function(btn){
  btn.addEventListener('click', function(e){
    e.preventDefault();
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    if (history.pushState) {
      history.pushState(null, null, '#top');
    }
  });
});
})();
