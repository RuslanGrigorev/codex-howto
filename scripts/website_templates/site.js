(function(){'use strict';
var p=window.CodexProgress;
var status=document.getElementById('status');
function message(text){if(status)status.textContent=text;}
if(p&&p.isStorageAvailable&&!p.isStorageAvailable()){message('Браузер не сохраняет прогресс. Экспортируйте JSON перед закрытием страницы.');}

var themeBtn=document.getElementById('theme-toggle');
function getTheme(){
  if(document.documentElement.dataset.theme) return document.documentElement.dataset.theme;
  try{
    var saved=localStorage.getItem('course-theme')||localStorage.getItem('theme');
    if(saved==='dark'||saved==='light')return saved;
  }catch(e){}
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  var isAutomated = typeof navigator !== 'undefined' && navigator.webdriver;
  return isAutomated ? (prefersDark ? 'dark' : 'light') : (prefersDark ? 'dark' : 'light');
}
var currentTheme=getTheme();
document.documentElement.dataset.theme=currentTheme;

function updateThemeButton(t){
  if(!themeBtn)return;
  themeBtn.setAttribute('aria-label',t==='dark'?'Включить светлую тему':'Включить тёмную тему');
  themeBtn.setAttribute('title',t==='dark'?'Включить светлую тему':'Включить тёмную тему');
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

  function tokenize(str) {
    var tokens = [];
    var current = '';
    var inDouble = false;
    var inSingle = false;
    for (var i = 0; i < str.length; i++) {
      var ch = str[i];
      if (ch === '"' && !inSingle) {
        inDouble = !inDouble;
      } else if (ch === "'" && !inDouble) {
        inSingle = !inSingle;
      } else if ((ch === ' ' || ch === '\t') && !inDouble && !inSingle) {
        if (current.length > 0) {
          tokens.push(current);
          current = '';
        }
      } else {
        current += ch;
      }
    }
    if (current.length > 0) {
      tokens.push(current);
    }
    return tokens;
  }

  var KNOWN_SUBCOMMANDS = [
    'exec', 'app-server', 'login', 'logout', 'resume', 'fork', 'archive', 'unarchive',
    'delete', 'review', 'apply', 'mcp', 'execpolicy', 'cloud', 'agents', 'queue',
    'plugin', 'remote-control', 'completion', 'features', 'sandbox', 'doctor', 'update', 'debug', 'mcp-server'
  ];

  var SUBCOMMAND_ALLOWED_FLAGS = {
    'exec': null,
    'doctor': ['--help', '-h'],
    'update': ['--help', '-h'],
    'login': ['--help', '-h'],
    'logout': ['--help', '-h'],
    'resume': ['--help', '-h'],
    'fork': ['--help', '-h'],
    'archive': ['--help', '-h'],
    'unarchive': ['--help', '-h'],
    'delete': ['--help', '-h'],
    'review': ['--help', '-h'],
    'apply': ['--help', '-h'],
    'mcp': ['--help', '-h'],
    'execpolicy': ['--help', '-h'],
    'cloud': ['--help', '-h'],
    'agents': ['--help', '-h'],
    'queue': ['--help', '-h'],
    'plugin': ['--help', '-h'],
    'remote-control': ['--help', '-h'],
    'completion': ['--help', '-h'],
    'features': ['--help', '-h'],
    'sandbox': ['--help', '-h'],
    'debug': ['--help', '-h'],
    'mcp-server': ['--help', '-h'],
    'app-server': ['--help', '-h']
  };

  var VALID_SANDBOX_VALUES = ['read-only', 'workspace-write', 'danger-full-access'];
  var VALID_APPROVAL_VALUES = ['untrusted', 'always', 'never'];

  var VALID_CODEX_FLAGS = {
    '--model': true, '-m': true,
    '--sandbox': true,
    '--ask-for-approval': true, '-a': true,
    '--cd': true, '-C': true,
    '--config': true, '-c': true,
    '--profile': true, '-p': true,
    '--mcp-config': true,
    '--agent': true,
    '--image': true, '-i': true,
    '--add-dir': true,
    '--search': false,
    '--oss': false, '--local-provider': false,
    '--continue': false, '--resume': false,
    '--help': false, '-h': false,
    '--version': false, '-V': false,
    '--strict-config': false,
    '--no-alt-screen': false,
    '--skip-git-repo-check': false
  };

  var VALID_EXEC_FLAGS = {
    '--json': false,
    '--ephemeral': false,
    '--output-schema': true,
    '--output-last-message': true, '-o': true,
    '--sandbox': true,
    '--ask-for-approval': true, '-a': true,
    '--cd': true, '-C': true,
    '--config': true, '-c': true,
    '--profile': true, '-p': true,
    '--model': true, '-m': true,
    '--help': false, '-h': false,
    '--version': false, '-V': false
  };

  function executeSim(rawCmd){
    var cmd = (rawCmd || '').trim();
    if(!cmd)return;
    appendLine('user@codex-lab:~$ ' + cmd, 'user-cmd-line');

    var tokens = tokenize(cmd);
    if(!tokens.length)return;

    var first = tokens[0].toLowerCase();

    if(first === 'clear'){
      output.replaceChildren();
      appendLine('[СИМУЛЯТОР CODEX CLI 0.160.0 ОЧИЩЕН]', 'system-line');
      return;
    }
    if(first === 'help' || first === '/help'){
      appendLine('[СИМУЛЯЦИЯ] Доступные команды симулятора Codex CLI 0.160.0:\n' +
        '  codex [ПАРАМЕТРЫ] [ПРОМПТ]\n' +
        '    --model <gpt-5 | gpt-4.1 | o3-mini>\n' +
        '    --sandbox <read-only | workspace-write | danger-full-access>\n' +
        '    --ask-for-approval <untrusted | always | never>\n' +
        '    --cd, -C <КАТАЛОГ>\n' +
        '    --config, -c <КЛЮЧ=ЗНАЧЕНИЕ>\n' +
        '    --continue, --help, --version (-V), exec, app-server\n' +
        '  Slash-команды сессии:\n' +
        '    /goal [/goal pause | /goal resume | /goal clear]\n' +
        '    /model [/model <название>]\n' +
        '    /permissions, /status, /skills, /mcp, /plugins, /hooks, /resume [<id>], /exit\n' +
        '  Навыки и проектные команды:\n' +
        '    $learn, cat AGENTS.md, clear');
      return;
    }
    if(first === 'cat'){
      if(tokens[1] && tokens[1].toLowerCase() === 'agents.md'){
        appendLine('# Инструкции проекта (AGENTS.md)\n' +
          '- Автономный практикум Codex CLI.\n' +
          '- Кодировка UTF-8.\n' +
          '- Строгая проверка контракта без сетевых вызовов.');
        return;
      }
      appendLine('[СИМУЛЯЦИЯ cat] Файл не найден или чтение ограничено.', 'error-line');
      return;
    }
    if(first === 'python'){
      if(cmd.includes('verify.py')){
        appendLine('[СИМУЛЯЦИЯ verify.py] CHK-CATALOG: PASS | CHK-SITE: PASS | CHK-SITE-LINKS: PASS | CHK-BROWSER: PASS\nИтог: автономный профиль проверен.');
        return;
      }
      appendLine('[СИМУЛЯЦИЯ python] Скрипт выполнен успешно.');
      return;
    }
    if(first === 'рид' || cmd.toLowerCase() === 'рид онли' || cmd.toLowerCase() === 'read-only' || cmd.toLowerCase() === 'read only'){
      appendLine('[СИМУЛЯЦИЯ: ПЕСОЧНИЦА] Режим песочницы: read-only (только чтение).\n' +
        'Все изменения файлов и деструктивные операции заблокированы. Агент работает исключительно в режиме анализа.');
      return;
    }
    if(first.startsWith('$')){
      appendLine('[СИМУЛЯЦИЯ ' + first + '] Навык проекта активен. Инструкции загружены в контекст.');
      return;
    }

    if(first.startsWith('/')){
      if(first === '/model'){
        if(tokens[1]){
          appendLine('[СИМУЛЯЦИЯ /model] Модель сессии успешно переключена на "' + tokens[1] + '". Контекст сохранён.');
        } else {
          appendLine('[СИМУЛЯЦИЯ /model] Текущая модель сессии: gpt-5 (OpenAI)\n' +
            'Доступные профили моделей (0.160.0):\n' +
            '  1. gpt-5 (по умолчанию: reasoning + coding)\n' +
            '  2. gpt-4.1 (быстрая кодогенерация и рефакторинг)\n' +
            '  3. o3-mini (структурированный анализ и валидация)\n' +
            'Для переключения модели используйте: /model <название>');
        }
        return;
      }
      if(first === '/goal'){
        var subG = tokens[1] ? tokens[1].toLowerCase() : '';
        if(subG === 'pause'){
          appendLine('[СИМУЛЯЦИЯ /goal] Долгосрочная цель приостановлена. Прогресс сохранён.');
        } else if(subG === 'resume'){
          appendLine('[СИМУЛЯЦИЯ /goal] Выполнение цели возобновлено с текущего шага.');
        } else if(subG === 'clear'){
          appendLine('[СИМУЛЯЦИЯ /goal] Текущая цель очищена.');
        } else {
          appendLine('[СИМУЛЯЦИЯ /goal] Текущая цель:\n' +
            '  1. [DONE] Исследование архитектуры и требований\n' +
            '  2. [IN_PROGRESS] Реализация и подготовка материалов\n' +
            '  3. [PENDING] Автономная верификация и сдача\n' +
            'Статус: АКТИВНА. Для паузы используйте: /goal pause');
        }
        return;
      }
      if(first === '/permissions'){
        appendLine('[СИМУЛЯЦИЯ /permissions] Права безопасности сессии:\n' +
          '  - sandbox: workspace-write (изменение только в рабочей области)\n' +
          '  - network: blocked (автономный офлайн-режим)\n' +
          '  - approvals: untrusted (запрос подтверждения на внешние действия)');
        return;
      }
      if(first === '/sandbox'){
        appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестная slash-команда "/sandbox". Команда /sandbox отсутствует в каноническом baseline 0.160.0. Используйте флаг CLI "codex --sandbox <режим>" или команду "/permissions".', 'error-line');
        return;
      }
      if(first === '/status'){
        appendLine('[СИМУЛЯЦИЯ /status]\n' +
          '  Сессия: active (id: sess-0160-mock)\n' +
          '  Модель: baseline-0.160.0\n' +
          '  Контекст: 2,450 / 128,000 токенов (1.9%)\n' +
          '  Режим: автономный офлайн');
        return;
      }
      if(first === '/skills'){
        appendLine('[СИМУЛЯЦИЯ /skills] Зарегистрированные навыки проекта:\n' +
          '  - $learn: автономный наставник курса Codex CLI\n' +
          '  - $project-map: построение карты проекта\n' +
          '  - $diff-review: аудит изменений');
        return;
      }
      if(first === '/mcp'){
        appendLine('[СИМУЛЯЦИЯ /mcp] Протокол Model Context Protocol (0.160.0):\n' +
          '  Подключение: stdio / SSE\n' +
          '  Конфигурация: mcp_config.json\n' +
          '  Доступных инструментов: 0');
        return;
      }
      if(first === '/plugins' || first === '/hooks'){
        appendLine('[СИМУЛЯЦИЯ] Зарегистрированные хуки: PreToolUse, PostToolUse, UserPromptSubmit, Stop.');
        return;
      }
      if(first === '/resume'){
        if(tokens[1]){
          appendLine('[СИМУЛЯЦИЯ /resume] Сессия "' + tokens[1] + '" успешно восстановлена.');
        } else {
          appendLine('[СИМУЛЯЦИЯ /resume] Сохранённые сессии в .codex/sessions:\n' +
            '  1. sess-2026-10-05-01 (активна)\n' +
            '  2. sess-2026-10-04-02 (завершена)\n' +
            'Для продолжения сессии используйте: /resume <id>');
        }
        return;
      }
      if(first === '/exit' || first === '/quit'){
        appendLine('[СИМУЛЯЦИЯ] Сессия Codex CLI завершена. Состояние сессии сохранено в .codex/sessions.');
        return;
      }
      if(first === '/plan'){
        appendLine('[СИМУЛЯЦИЯ /plan] Режим планирования активен. Сформируйте требования до изменения кода.');
        return;
      }
      if(first === '/diff'){
        appendLine('[СИМУЛЯЦИЯ /diff] Изменений в рабочей копии нет (чистый рабочий каталог).');
        return;
      }
      if(first === '/review'){
        appendLine('[СИМУЛЯЦИЯ /review] Запрос автономного ревью diff запущен. Проверка завершена: замечаний нет.');
        return;
      }
      if(first === '/version'){
        appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестная slash-команда "/version". Для вывода версии используйте команду CLI "codex --version" или "codex -V".', 'error-line');
        return;
      }
      appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестная slash-команда "' + first + '". В Codex CLI 0.160.0 используйте /help для списка поддерживаемых команд.', 'error-line');
      return;
    }

    if(first === 'exit'){
      appendLine('[СИМУЛЯЦИЯ] Сессия Codex CLI завершена. Состояние сессии сохранено в .codex/sessions.');
      return;
    }

    if(first === 'codex'){
      var args = tokens.slice(1);
      if(!args.length){
        appendLine('[СИМУЛЯЦИЯ] Интерактивная сессия Codex CLI 0.160.0 запущена.\n' +
          '  Рабочий каталог: /workspace\n' +
          '  Модель: gpt-5\n' +
          '  Песочница: workspace-write\n' +
          '  Подтверждения: untrusted\n' +
          '  Сеть: disabled (автономный режим)\n' +
          'Введите задачу или команду (/goal, /model, /permissions, /status). Для выхода: /exit');
        return;
      }

      var a0 = args[0].toLowerCase();
      if(a0 === '--help' || a0 === '-h'){
        appendLine(
          'Codex CLI v0.160.0 (rust-v0.160.0)\n\n' +
          'Использование: codex [ПАРАМЕТРЫ] [КОМАНДА] [ПРОМПТ]\n\n' +
          'Подкоманды:\n' +
          '  exec         Неинтерактивное пакетное выполнение промпта\n' +
          '  app-server   Запуск stdio JSON-RPC 2.0 сервера интеграции\n\n' +
          'Параметры:\n' +
          '  -m, --model <МОДЕЛЬ>         Целевая модель (gpt-5, gpt-4.1)\n' +
          '  --sandbox <РЕЖИМ>            Режим: read-only | workspace-write | danger-full-access\n' +
          '  -a, --ask-for-approval <РЕЖ> Запрос подтверждения: untrusted | always | never\n' +
          '  -C, --cd <КАТАЛОГ>           Рабочий каталог\n' +
          '  -c, --config <КЛЮЧ=ЗНАЧ>     Переопределение конфигурации TOML\n' +
          '  --mcp-config <ФАЙЛ>          Путь к конфигурации MCP\n' +
          '  --continue, --resume         Возобновление сессии\n' +
          '  -h, --help                   Справка\n' +
          '  -V, --version                Версия'
        );
        return;
      }
      if(a0 === '--version' || a0 === '-v' || a0 === '-V'){
        appendLine('codex 0.160.0 (offline docs baseline rust-v0.160.0)');
        return;
      }
      if(a0 === 'app-server'){
        appendLine('[СИМУЛЯЦИЯ app-server] Сервер JSON-RPC 2.0 ожидает входящие запросы в stdin.');
        return;
      }

      if(a0 === 'exec'){
        var execArgs = args.slice(1);
        var execPrompt = [];
        for(var ei = 0; ei < execArgs.length; ei++){
          var etok = execArgs[ei];
          if(etok.startsWith('-')){
            var normEtok = etok.startsWith('--') ? etok.toLowerCase() : etok;
            if(VALID_EXEC_FLAGS[normEtok] === undefined){
              appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестный параметр команды codex exec: "' + etok + '". Введите "codex exec --help" для списка параметров.', 'error-line');
              return;
            }
            if(VALID_EXEC_FLAGS[normEtok] === true){
              ei++;
              if(ei >= execArgs.length){
                appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Параметр "' + etok + '" требует аргумент.', 'error-line');
                return;
              }
              var evalVal = execArgs[ei];
              if(normEtok === '--sandbox'){
                if(VALID_SANDBOX_VALUES.indexOf(evalVal) === -1){
                  appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Недопустимое значение для --sandbox: "' + evalVal + '". Разрешённые режимы: ' + VALID_SANDBOX_VALUES.join(', ') + '.', 'error-line');
                  return;
                }
              } else if(normEtok === '--ask-for-approval' || normEtok === '-a'){
                if(VALID_APPROVAL_VALUES.indexOf(evalVal) === -1){
                  appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Недопустимое значение для --ask-for-approval: "' + evalVal + '". Разрешённые значения: ' + VALID_APPROVAL_VALUES.join(', ') + '.', 'error-line');
                  return;
                }
              }
            }
          } else {
            execPrompt.push(etok);
          }
        }
        var pText = execPrompt.join(' ') || 'задача';
        appendLine('[СИМУЛЯЦИЯ exec] Неинтерактивное выполнение (0.160.0):\n' +
          '{"type":"session.start","version":"0.160.0","mode":"exec"}\n' +
          '{"type":"item.create","item":{"type":"message","role":"user","content":"' + pText.replace(/"/g, '\\"') + '"}}\n' +
          '{"type":"agent.response","status":"completed","exit_code":0}\n' +
          'Завершено с кодом 0 (успешно).');
        return;
      }

      if(KNOWN_SUBCOMMANDS.indexOf(a0) !== -1){
        var subArgs = args.slice(1);
        var allowed = SUBCOMMAND_ALLOWED_FLAGS[a0] || ['--help', '-h'];
        for(var si = 0; si < subArgs.length; si++){
          var stok = subArgs[si];
          if(stok.startsWith('-')){
            var normStok = stok.startsWith('--') ? stok.toLowerCase() : stok;
            if(allowed.indexOf(normStok) === -1){
              appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестный параметр команды codex ' + a0 + ': "' + stok + '".', 'error-line');
              return;
            }
          }
        }
        appendLine('[СИМУЛЯЦИЯ ' + a0 + '] Подкоманда baseline 0.160.0 принята к исполнению.');
        return;
      }

      if(a0.startsWith('exec') && a0 !== 'exec'){
        appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестная подкоманда "' + args[0] + '". Вы имели в виду "codex exec"? Введите "codex --help" для списка подкоманд.', 'error-line');
        return;
      }

      var curModel = 'gpt-5';
      var curSandbox = 'workspace-write';
      var curApp = 'untrusted';
      var curAgent = null;
      var curSkill = null;
      var curMcp = null;
      var isCont = false;
      var promptParts = [];

      for(var ai = 0; ai < args.length; ai++){
        var atok = args[ai];
        if(atok.startsWith('-')){
          var normAtok = atok.startsWith('--') ? atok.toLowerCase() : atok;
          if(VALID_CODEX_FLAGS[normAtok] === undefined){
            appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестный параметр команды codex: "' + atok + '". Введите "codex --help" для списка поддерживаемых параметров.', 'error-line');
            return;
          }
          if(VALID_CODEX_FLAGS[normAtok] === true){
            ai++;
            if(ai >= args.length){
              appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Параметр "' + atok + '" требует аргумент.', 'error-line');
              return;
            }
            var aval = args[ai];
            if(normAtok === '--model' || normAtok === '-m') curModel = aval;
            if(normAtok === '--sandbox'){
              if(VALID_SANDBOX_VALUES.indexOf(aval) === -1){
                appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Недопустимое значение для --sandbox: "' + aval + '". Разрешённые режимы: ' + VALID_SANDBOX_VALUES.join(', ') + '.', 'error-line');
                return;
              }
              curSandbox = aval;
            }
            if(normAtok === '--ask-for-approval' || normAtok === '-a'){
              if(VALID_APPROVAL_VALUES.indexOf(aval) === -1){
                appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Недопустимое значение для --ask-for-approval: "' + aval + '". Разрешённые значения: ' + VALID_APPROVAL_VALUES.join(', ') + '.', 'error-line');
                return;
              }
              curApp = aval;
            }
            if(normAtok === '--agent') curAgent = aval;
            if(normAtok === '--mcp-config') curMcp = aval;
          } else {
            if(normAtok === '--continue' || normAtok === '--resume') isCont = true;
          }
        } else if(atok.startsWith('$')){
          curSkill = atok;
        } else {
          promptParts.push(atok);
        }
      }

      var sbDesc = curSandbox.includes('read-only') ? 'read-only (только чтение: запись файлов заблокирована)' : curSandbox;
      var outLines = [
        '[СИМУЛЯЦИЯ] Интерактивная сессия Codex CLI 0.160.0 запущена.',
        '  Рабочий каталог: /workspace',
        '  Модель: ' + curModel,
        '  Песочница: ' + sbDesc,
        '  Подтверждения: ' + curApp,
        '  Сеть: disabled (автономный режим)'
      ];
      if(curAgent) outLines.push('  Субагент: ' + curAgent + ' (ролевой профиль активен)');
      if(curSkill) outLines.push('  Навык: ' + curSkill + ' (инструкции навыка загружены в контекст)');
      if(curMcp) outLines.push('  MCP: конфигурация "' + curMcp + '" загружена');
      if(isCont) outLines.push('  Возобновление: последняя активная сессия восстановлена');
      if(promptParts.length) outLines.push('  Начальный промпт: "' + promptParts.join(' ') + '"');
      outLines.push('Введите задачу или команду (/goal, /model, /permissions, /status). Для выхода: /exit');
      appendLine(outLines.join('\n'));
      return;
    }

    appendLine('[СИМУЛЯЦИЯ: ОШИБКА] Неизвестная команда или опция "' + cmd + '". В Codex CLI 0.160.0 используйте /help для списка поддерживаемых команд.', 'error-line');
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

if ('IntersectionObserver' in window) {
  var tocLinks = document.querySelectorAll('.toc-sidebar .toc-link');
  if (tocLinks.length > 0) {
    var linkMap = {};
    tocLinks.forEach(function(l){
      var id = l.getAttribute('href');
      if (id && id.startsWith('#')) {
        linkMap[id.substring(1)] = l;
        l.addEventListener('click', function(e){
          var target = document.getElementById(id.substring(1));
          if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            if (history.pushState) {
              history.pushState(null, null, '#' + id.substring(1));
            }
          }
        });
      }
    });
    var headings = document.querySelectorAll('.prose h2[id], .prose h3[id]');
    var observer = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if (entry.isIntersecting) {
          var id = entry.target.id;
          if (linkMap[id]) {
            tocLinks.forEach(function(lnk){ lnk.classList.remove('active'); });
            linkMap[id].classList.add('active');
          }
        }
      });
    }, { rootMargin: '0px 0px -70% 0px' });
    headings.forEach(function(h){ observer.observe(h); });
  }
}

// Mobile navigation drawer toggle
var navToggle = document.getElementById('nav-toggle');
var sidebarClose = document.getElementById('sidebar-close');
var sidebarBackdrop = document.getElementById('sidebar-backdrop');
var courseSidebar = document.getElementById('course-sidebar');

function openSidebar() {
  document.body.classList.add('sidebar-open');
  if (navToggle) navToggle.setAttribute('aria-expanded', 'true');
}
function closeSidebar() {
  document.body.classList.remove('sidebar-open');
  if (navToggle) navToggle.setAttribute('aria-expanded', 'false');
}

if (navToggle) {
  navToggle.addEventListener('click', function(e) {
    e.stopPropagation();
    if (document.body.classList.contains('sidebar-open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });
}
if (sidebarClose) {
  sidebarClose.addEventListener('click', closeSidebar);
}
if (sidebarBackdrop) {
  sidebarBackdrop.addEventListener('click', closeSidebar);
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
    closeSidebar();
  }
});
if (courseSidebar) {
  courseSidebar.querySelectorAll('a').forEach(function(link) {
    link.addEventListener('click', function() {
      if (window.innerWidth <= 860) {
        closeSidebar();
      }
    });
  });
}

})();
