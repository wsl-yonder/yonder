(() => {
  const localNovels = [
    {
      id: "sky-forge",
      title: "天工问道",
      author: "青铜书生",
      gender: "男频",
      category: "玄幻",
      status: "连载",
      words: 2860000,
      hot: 9850,
      updated: "2026-05-10",
      tags: ["东方玄幻", "宗门", "炼器"],
      colors: ["#7d3f26", "#d58a4a"],
      summary: "少年在废弃矿山捡到一枚会说话的古炉，从外门杂役一路走到万族战场。每一次锻造，都是一次与天地规则的谈判。",
      chapters: [
        { title: "第一章 山雨欲来", content: ["云州北境的雨总是来得很急。陆沉背着半袋黑铁矿，从山道上下来时，远处的雷声已经压到了矿棚顶上。", "他是青岚宗最不起眼的杂役，负责给炼器堂送矿。可今天的矿车里，多了一枚没人认得的青铜小炉。", "小炉在雨声里轻轻震了一下，像有人在里面敲门。陆沉低头，听见一个沙哑的声音说：小子，想不想看看真正的火。"] },
        { title: "第二章 炉中有火", content: ["夜半，杂役院的人都睡了。陆沉把青铜炉放在窗前，炉壁上的裂纹像星河一样亮起来。", "一缕白火从炉口探出，没烧焦桌面，却把他掌心旧伤照得透明。那声音又响起：你的骨头不错，可惜被人封过。", "陆沉第一次知道，自己并不是不能修行，而是有人不希望他修行。"] },
        { title: "第三章 外门试炼", content: ["三日后，青岚宗外门试炼开场。陆沉站在人群最后，袖中藏着一枚被白火重炼过的铁符。", "长老念到他的名字时，许多人笑出了声。一个杂役也敢上试炼台，这在青岚宗很多年没有发生过。", "陆沉没有解释。他只是握紧铁符，听见炉中老人低声说：别怕，今日先砸一座门。"] }
      ]
    },
    {
      id: "neon-gunner",
      title: "霓虹枪火",
      author: "夜航员",
      gender: "男频",
      category: "都市",
      status: "连载",
      words: 1460000,
      hot: 9020,
      updated: "2026-05-09",
      tags: ["都市异能", "赛博", "热血"],
      colors: ["#253858", "#00a8b5"],
      summary: "旧城区快递员意外绑定城市防火墙，在霓虹雨夜里追查失踪算法与地下财团。",
      chapters: [
        { title: "第一章 雨夜快件", content: ["江北旧城凌晨两点，雨水把招牌灯洗成一片模糊的红。林野骑着电动车穿过窄巷，怀里揣着一个没有寄件人的包裹。", "包裹很轻，却在靠近市政数据塔时发出心跳一样的震动。", "他停在塔下，手机屏幕忽然黑了，只剩一行字：临时防火墙已上线，宿主林野。"] },
        { title: "第二章 黑市频道", content: ["林野以为自己撞上了诈骗软件，直到一辆无人车从雨幕里冲出来，精准地撞向他的膝盖。", "世界在那一秒慢了下来。街边摄像头、交通信号、广告屏，全都变成可被他触碰的线。", "他抬手，红灯变绿，无人车擦着他的衣角冲进河里。"] },
        { title: "第三章 第七码头", content: ["黑市频道里有人悬赏他的名字。赏金不高，却足够让旧城所有赏金猎人兴奋一整夜。", "林野躲进第七码头的废仓库，看见墙上贴着一张失踪名单。", "名单第一行，是他三年前消失的姐姐。"] }
      ]
    },
    {
      id: "guild-zero",
      title: "零号公会",
      author: "键盘骑士",
      gender: "男频",
      category: "网游",
      status: "完结",
      words: 3180000,
      hot: 8760,
      updated: "2026-04-28",
      tags: ["虚拟网游", "公会", "竞技"],
      colors: ["#2f4b2f", "#9dbb62"],
      summary: "退役指挥重回全息网游，从无人问津的新手村建立第一支跨服公会。",
      chapters: [
        { title: "第一章 重登账号", content: ["陈越输入旧密码时，游戏舱提示该账号已经沉睡一千一百二十七天。", "他曾经是联盟赛最年轻的战术指挥，后来在总决赛前夜突然退役。", "今天，他只想安静钓鱼。系统却把他投放到了一个正在被魔潮围攻的新手村。"] },
        { title: "第二章 新手村守卫战", content: ["村口只有十二名玩家，职业乱七八糟，装备更像临时拼出来的玩具。", "陈越扫了一眼地形，开始分配站位。没人认识他，却没人能拒绝那种干净利落的语气。", "第一波魔潮撞上木栅栏时，新手村的反击像一台刚修好的旧机器，重新转了起来。"] },
        { title: "第三章 第一面旗", content: ["守卫战结束后，系统奖励了一面空白公会旗。", "陈越本想卖掉，换一根更好的鱼竿。可那个叫小满的治疗玩家问他：队长，明天还打吗？", "他沉默很久，在旗面上写下两个字：零号。"] }
      ]
    },
    {
      id: "spring-letter",
      title: "春日来信",
      author: "鹿眠",
      gender: "女频",
      category: "言情",
      status: "连载",
      words: 680000,
      hot: 9400,
      updated: "2026-05-10",
      tags: ["久别重逢", "治愈", "甜文"],
      colors: ["#a75b6a", "#f2a6b3"],
      summary: "插画师回到海边小城整理外婆旧屋，收到一封寄迟了七年的信，也遇见当年没有告别的人。",
      chapters: [
        { title: "第一章 旧屋钥匙", content: ["温梨回到南屿时，车站外的木棉花开得正盛。她拖着行李箱，手心里攥着外婆留下的旧屋钥匙。", "钥匙齿口有一道缺痕，是小时候她摔在青石阶上磕出来的。", "她以为这趟回来只是整理遗物，直到在门缝里发现一封寄给自己的信。"] },
        { title: "第二章 七年前的邮戳", content: ["信封上的邮戳来自七年前的春天，收件人写着温梨，字迹却陌生又熟悉。", "她拆开信，第一句话是：如果你看到这里，说明我还是没能当面向你道歉。", "落款处只有一个字，沈。"] },
        { title: "第三章 海风与重逢", content: ["傍晚，温梨去修旧屋漏水的窗。维修师傅站在门外，白衬衫被海风吹得微微鼓起。", "他抬头时，两个人都愣住了。", "沈砚说：好久不见。温梨忽然觉得，七年的海风全都吹回了这个小院。"] }
      ]
    },
    {
      id: "palace-lamp",
      title: "长安灯影",
      author: "照夜清",
      gender: "女频",
      category: "古言",
      status: "完结",
      words: 1220000,
      hot: 8650,
      updated: "2026-04-30",
      tags: ["权谋", "宫廷", "双强"],
      colors: ["#52333f", "#c9985a"],
      summary: "女官执掌灯坊，却在一盏失窃宫灯里发现朝堂旧案的线索。",
      chapters: [
        { title: "第一章 灯坊失火", content: ["长安入夜，宫城万灯齐明。掌灯女官谢怀珠刚查完灯册，西侧灯坊便起了火。", "火势不大，却烧掉了皇后寿宴要用的百鸟朝凤灯。", "灰烬里，谢怀珠捡到一枚不该出现在宫中的军印碎片。"] },
        { title: "第二章 雁门旧案", content: ["军印属于雁门军，而雁门军七年前已经全军覆没。", "谢怀珠把碎片藏进袖中，转身就撞见新任大理寺少卿裴照。", "裴照看着她，像看着一盏快要烧尽的灯：谢女官，有些火不能碰。"] },
        { title: "第三章 夜审宫灯", content: ["寿宴前夜，谢怀珠重制宫灯。灯骨展开时，她在夹层里看见一张血书。", "血书上的名字，正是当今最受宠的国舅。", "窗外风雪骤起，裴照敲门而入：现在，你还要点这盏灯吗？"] }
      ]
    },
    {
      id: "star-archive",
      title: "群星档案",
      author: "南极电台",
      gender: "男频",
      category: "科幻",
      status: "连载",
      words: 1740000,
      hot: 8110,
      updated: "2026-05-08",
      tags: ["星际", "档案员", "文明"],
      colors: ["#24324f", "#7f9ed8"],
      summary: "星际档案员在整理失落文明记录时，发现人类历史被删除过三次。",
      chapters: [
        { title: "第一章 冷库档案", content: ["木星轨道外，第三档案冷库沉睡了四百年。沈聆接到调令时，只知道那里保存着七十万个失落文明的遗言。", "冷库管理员交给她第一份档案，封面上写着：人类，第三版。", "她以为是标注错误，直到看见档案里的地球坐标。"] },
        { title: "第二章 被删除的年份", content: ["档案显示，人类文明曾在公元二十一世纪末完成第一次星际跃迁。", "可是官方历史里，那一年只有漫长的能源危机。", "沈聆把资料导入私人终端，屏幕上弹出红色警告：你正在恢复已删除纪元。"] },
        { title: "第三章 第四次广播", content: ["冷库深处响起一段来自太阳系内的广播。", "声音断断续续，却清楚地念出她的名字。", "沈聆终于明白，档案不是过去，而是有人留给未来的求救信。"] }
      ]
    },
    {
      id: "mist-case",
      title: "雾港第七案",
      author: "白昼侦探",
      gender: "男频",
      category: "悬疑",
      status: "连载",
      words: 540000,
      hot: 7920,
      updated: "2026-05-06",
      tags: ["推理", "刑侦", "港城"],
      colors: ["#2d3740", "#8f9aa3"],
      summary: "雾港连环旧案重启，退休画像师被迫回到警署，面对一个模仿自己笔迹的凶手。",
      chapters: [
        { title: "第一章 画像", content: ["雾港的早晨看不见海。周岑推开画室门时，门口放着一个牛皮纸袋。", "纸袋里是一张未完成的嫌疑人画像，用的是他十年前才会用的笔法。", "背面写着：第七案，还差最后一笔。"] },
        { title: "第二章 旧警号", content: ["警署的人来得很快。年轻警官递给周岑一枚旧警号，说这是现场留下的。", "那枚警号属于他的搭档，一个已经在七年前殉职的人。", "周岑没有说话，只把画像翻过来，看见纸角有一点潮湿的灰。"] },
        { title: "第三章 雾中人", content: ["案发地在旧码头，雾浓得像一堵墙。", "周岑站在仓库门口，忽然听见有人用搭档的声音叫他的名字。", "他回头，只看见雾里有一道影子，手里拿着一支炭笔。"] }
      ]
    },
    {
      id: "kitchen-queen",
      title: "她的烟火厨房",
      author: "小满汤圆",
      gender: "女频",
      category: "都市",
      status: "连载",
      words: 760000,
      hot: 8340,
      updated: "2026-05-07",
      tags: ["美食", "创业", "成长"],
      colors: ["#8a4f2d", "#e6b468"],
      summary: "被裁员的产品经理开了一家深夜小食堂，用一道道家常菜治愈城市里晚归的人。",
      chapters: [
        { title: "第一章 最后一班地铁", content: ["何安宁被裁员那天，赶上了最后一班地铁。车厢里只有三个乘客，每个人都像被生活熬过一遍。", "她回到出租屋，发现楼下转角那间小铺正在招租。", "玻璃门上贴着四个字：可做餐饮。"] },
        { title: "第二章 番茄牛腩", content: ["小食堂开张第一晚，只有一个客人。男人穿着皱巴巴的西装，要了一份菜单上没有的番茄牛腩。", "何安宁本想拒绝，却想起妈妈以前总说，深夜想吃的东西，多半不是为了填饱肚子。", "她进了厨房，开火，切番茄。"] },
        { title: "第三章 深夜菜单", content: ["第二天，门口多了一张手写菜单。", "第一行是番茄牛腩，第二行空着。何安宁写下：你想吃什么，可以告诉我。", "晚上九点，门铃响了。"] }
      ]
    },
    {
      id: "immortal-market",
      title: "人间仙市",
      author: "折梅客",
      gender: "男频",
      category: "仙侠",
      status: "连载",
      words: 2030000,
      hot: 8460,
      updated: "2026-05-05",
      tags: ["修仙", "市井", "群像"],
      colors: ["#315346", "#8bbf9f"],
      summary: "凡人掌柜继承一座只在月圆夜开门的仙市，买卖灵物，也买卖人心。",
      chapters: [
        { title: "第一章 月圆开市", content: ["江陵城南有家旧铺，白天卖纸伞，夜里卖风。", "沈却继承铺子那晚，月亮圆得像一枚银钱。铺门自动打开，门外站着一队没有影子的客人。", "为首的青衣女子问：掌柜，今夜仙市可开？"] },
        { title: "第二章 一两春风", content: ["第一桩生意是一两春风。客人用三十年寿数来换，只为让病榻上的妻子再闻一次故乡花香。", "沈却不敢收。账册却自己翻开，写下价格公道四个字。", "他这才知道，仙市从不做亏本买卖。"] },
        { title: "第三章 伞下妖狐", content: ["雨夜，一只受伤的白狐钻进纸伞堆。", "它口吐人言，说有人在仙市里卖假命格。", "沈却合上铺门，第一次主动点亮了门口那盏青灯。"] }
      ]
    },
    {
      id: "mecha-dawn",
      title: "破晓机甲",
      author: "钢羽",
      gender: "男频",
      category: "科幻",
      status: "连载",
      words: 2340000,
      hot: 8230,
      updated: "2026-05-04",
      tags: ["机甲", "学院", "战争"],
      colors: ["#45464a", "#d66f4d"],
      summary: "边境维修工考入联邦机甲学院，却发现自己的残旧机体来自失踪王牌部队。",
      chapters: [
        { title: "第一章 废铁编号", content: ["边境废场里，编号D-17的旧机甲趴在沙地上，像一头死去多年的钢铁巨兽。", "许临每天负责拆废件，却从没见过会在夜里自启动的废铁。", "屏幕亮起时，系统只说了一句话：王牌序列，等待驾驶员。"] },
        { title: "第二章 入学测试", content: ["联邦机甲学院的入学测试不允许使用废弃机体。", "许临把D-17开进考场时，全场都在笑。", "三分钟后，笑声停了。那台旧机甲用最基础的推进器完成了王牌规避动作。"] },
        { title: "第三章 破晓徽章", content: ["考官在机体胸甲里发现一枚徽章。", "徽章属于十年前消失在破晓战役里的第九小队。", "许临看着徽章背面的名字，发现那是他父亲。"] }
      ]
    },
    {
      id: "moon-office",
      title: "月亮事务所",
      author: "禾年",
      gender: "女频",
      category: "悬疑",
      status: "连载",
      words: 640000,
      hot: 7730,
      updated: "2026-05-03",
      tags: ["轻悬疑", "奇幻", "单元剧"],
      colors: ["#4b3f63", "#bfa8e8"],
      summary: "只在凌晨营业的事务所，专门处理人们不愿承认的遗憾。",
      chapters: [
        { title: "第一章 凌晨委托", content: ["许知夏第一次看见月亮事务所，是在凌晨一点十七分。", "店门夹在两栋楼之间，白天那里明明只是一面墙。", "柜台后的男人递给她一张委托单：请写下你最想找回的东西。"] },
        { title: "第二章 丢失的声音", content: ["委托人是一名歌手，她丢失的不是嗓子，而是唱给某个人听的勇气。", "许知夏跟着线索走进旧剧院，舞台中央放着一只会录梦的八音盒。", "盒子打开时，她听见了自己的哭声。"] },
        { title: "第三章 墙后的门", content: ["事务所老板说，每个人心里都有一扇不肯打开的门。", "许知夏不信，直到那面墙在她面前裂开。", "门后站着的，是五年前没能告别的自己。"] }
      ]
    },
    {
      id: "football-age",
      title: "绿茵年代",
      author: "远射",
      gender: "男频",
      category: "体育",
      status: "完结",
      words: 1560000,
      hot: 7510,
      updated: "2026-04-18",
      tags: ["足球", "重生", "竞技"],
      colors: ["#2f613d", "#c8d85a"],
      summary: "失意教练回到十八岁，重新选择那条被伤病改变的绿茵路。",
      chapters: [
        { title: "第一章 回到球场", content: ["哨声响起时，周燃以为自己又在做梦。", "他低头，看见十八岁的双腿，膝盖还没有那道毁掉职业生涯的伤疤。", "球从中场滚来，所有人都在喊他的名字。"] },
        { title: "第二章 第一脚传球", content: ["周燃没有选择射门，而是把球传向无人注意的左路。", "队友愣了一下，随后起脚破门。", "教练在场边看着他，眼神第一次变得认真。"] },
        { title: "第三章 旧伤之前", content: ["比赛结束，周燃坐在更衣室里，盯着自己的膝盖。", "他知道三个月后会发生什么。", "这一次，他要改变的不只是自己，还有整支球队的命运。"] }
      ]
    }
  ];
  let novels = [...localNovels];

  const state = {
    source: "local",
    gender: "全部",
    category: "全部",
    query: "",
    sort: "updated",
    readerSize: Number(localStorage.getItem("novelReaderSize") || 19),
    readerTheme: localStorage.getItem("novelReaderTheme") || "paper",
  };

  const views = {
    library: document.querySelector('[data-view="library"]'),
    detail: document.querySelector('[data-view="detail"]'),
    reader: document.querySelector('[data-view="reader"]'),
  };
  const grid = document.querySelector("[data-book-grid]");
  const resultCount = document.querySelector("[data-result-count]");
  const search = document.querySelector("[data-search]");
  const sort = document.querySelector("[data-sort]");
  const genderFilters = document.querySelector("[data-gender-filters]");
  const categoryFilters = document.querySelector("[data-category-filters]");
  const sourceName = document.querySelector("[data-source-name]");
  const sourceNote = document.querySelector("[data-source-note]");
  const sourceButtons = [...document.querySelectorAll("[data-source]")];

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
  const formatWords = (value) => `${(value / 10000).toFixed(value >= 1000000 ? 0 : 1)}万字`;
  const progressKey = (id) => `novelProgress:${id}`;
  const setView = (name) => {
    Object.entries(views).forEach(([key, el]) => {
      el.hidden = key !== name;
    });
    const top = document.querySelector("#novel-app").getBoundingClientRect().top + window.scrollY - 18;
    window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
  };

  const getNovel = (id) => novels.find((novel) => novel.id === id);
  const getProgress = (id) => {
    const raw = localStorage.getItem(progressKey(id));
    return raw ? Number(raw) : 0;
  };
  const saveProgress = (id, chapterIndex) => {
    localStorage.setItem(progressKey(id), String(chapterIndex));
  };

  function syncSourceHeader() {
    sourceButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.source === state.source));
    if (state.source === "gutenberg") {
      sourceName.textContent = "Project Gutenberg 中文公版书";
      sourceNote.textContent = "真实公版书源。点击书籍时会按需拉取纯文本并切分章节，仍使用本站阅读器。";
    } else {
      sourceName.textContent = "本地 Demo 书库";
      sourceNote.textContent = "用于验证搜索、目录和阅读器交互的本地示例书库。";
    }
  }

  async function loadGutenbergLibrary() {
    sourceName.textContent = "正在加载 Project Gutenberg...";
    sourceNote.textContent = "通过本地代理读取 Gutendex 中文公版书元数据。";
    const response = await fetch(`/api/novels/gutenberg?q=${encodeURIComponent(state.query.trim())}`);
    if (!response.ok) throw new Error("书源加载失败");
    const payload = await response.json();
    novels = payload.books || [];
    state.gender = "全部";
    state.category = "全部";
    syncSourceHeader();
    renderLibrary();
  }

  async function loadGutenbergDetail(novel) {
    views.detail.innerHTML = `<div class="empty-state">正在从 ${escapeHtml(novel.sourceName || "书源")} 读取《${escapeHtml(novel.title)}》正文...</div>`;
    setView("detail");
    const response = await fetch(`/api/novels/gutenberg/${novel.externalId}`);
    if (!response.ok) throw new Error("正文加载失败");
    const detail = await response.json();
    Object.assign(novel, detail);
    return novel;
  }

  function renderChips() {
    const genders = ["全部", ...new Set(novels.map((novel) => novel.gender))];
    const categories = ["全部", ...new Set(novels.map((novel) => novel.category))];
    genderFilters.innerHTML = genders.map((name) => `<button class="filter-chip ${state.gender === name ? "is-active" : ""}" data-gender="${escapeHtml(name)}">${escapeHtml(name)}</button>`).join("");
    categoryFilters.innerHTML = categories.map((name) => `<button class="filter-chip ${state.category === name ? "is-active" : ""}" data-category="${escapeHtml(name)}">${escapeHtml(name)}</button>`).join("");
  }

  function filteredNovels() {
    const query = state.query.trim().toLowerCase();
    return novels
      .filter((novel) => state.gender === "全部" || novel.gender === state.gender)
      .filter((novel) => state.category === "全部" || novel.category === state.category)
      .filter((novel) => {
        if (!query) return true;
        return [novel.title, novel.author, novel.category, novel.summary, ...novel.tags].join(" ").toLowerCase().includes(query);
      })
      .sort((a, b) => {
        if (state.sort === "hot") return b.hot - a.hot;
        if (state.sort === "words") return b.words - a.words;
        if (state.sort === "title") return a.title.localeCompare(b.title, "zh-Hans-CN");
        return b.updated.localeCompare(a.updated);
      });
  }

  function renderLibrary() {
    renderChips();
    const books = filteredNovels();
    resultCount.textContent = `${books.length} 本书`;
    grid.innerHTML = books.length
      ? books.map((novel) => `
        <a class="book-card" href="#novel/${novel.id}" data-open-detail="${novel.id}">
          <div class="book-cover" style="--cover-a:${escapeHtml(novel.colors[0])};--cover-b:${escapeHtml(novel.colors[1])}"><b>${escapeHtml(novel.title)}</b></div>
          <div class="book-meta">
            <h3>${escapeHtml(novel.title)}</h3>
            <p>${escapeHtml(novel.author)} · ${escapeHtml(novel.gender)} · ${escapeHtml(novel.category)}</p>
            <p>${escapeHtml(novel.summary)}</p>
            <div class="book-tags">${novel.tags.slice(0, 3).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div>
            <p>${escapeHtml(novel.status)} · ${formatWords(novel.words)} · 更新 ${escapeHtml(novel.updated)}</p>
          </div>
        </a>`).join("")
      : `<div class="empty-state">没有找到匹配的小说，换个关键词试试。</div>`;
  }

  async function renderDetail(novel) {
    if (novel.needsLoad) {
      try {
        novel = await loadGutenbergDetail(novel);
      } catch (error) {
        views.detail.innerHTML = `<div class="empty-state">书源正文读取失败：${escapeHtml(error.message)}</div>`;
        setView("detail");
        return;
      }
    }
    const progress = getProgress(novel.id);
    views.detail.innerHTML = `
      <div class="detail-layout">
        <div class="detail-cover" style="--cover-a:${escapeHtml(novel.colors[0])};--cover-b:${escapeHtml(novel.colors[1])}"><b>${escapeHtml(novel.title)}</b></div>
        <div class="detail-copy">
          <button class="ghost-btn" data-back-library>返回书库</button>
          <h2>${escapeHtml(novel.title)}</h2>
          <p>${escapeHtml(novel.author)} · ${escapeHtml(novel.gender)} · ${escapeHtml(novel.category)}</p>
          <div class="detail-stats">
            <span>${escapeHtml(novel.status)}</span>
            <span>${formatWords(novel.words)}</span>
            <span>热度 ${novel.hot}</span>
            <span>更新 ${escapeHtml(novel.updated)}</span>
          </div>
          <p>${escapeHtml(novel.summary)}</p>
          <div class="book-tags">${novel.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div>
          <div class="action-row">
            <button class="primary-btn" data-read="${novel.id}" data-chapter="0">开始阅读</button>
            <button class="ghost-btn" data-read="${novel.id}" data-chapter="${progress}">继续上次阅读</button>
            ${novel.sourceUrl ? `<a class="ghost-btn" href="${escapeHtml(novel.sourceUrl)}" target="_blank" rel="noopener noreferrer">查看来源</a>` : ""}
          </div>
        </div>
      </div>
      <section class="chapter-list">
        <h3>目录</h3>
        ${novel.chapters.map((chapter, index) => `
          <button data-read="${novel.id}" data-chapter="${index}">
            <span>${escapeHtml(chapter.title)}</span>
            <small>${index === progress ? "上次读到" : "阅读"}</small>
          </button>`).join("")}
      </section>`;
    setView("detail");
  }

  function applyReaderTheme() {
    views.reader.classList.remove("theme-night", "theme-green");
    if (state.readerTheme === "night") views.reader.classList.add("theme-night");
    if (state.readerTheme === "green") views.reader.classList.add("theme-green");
    views.reader.style.setProperty("--reader-size", `${state.readerSize}px`);
  }

  function renderReader(novel, chapterIndex) {
    if (!novel.chapters.length) {
      renderDetail(novel);
      return;
    }
    const index = Math.max(0, Math.min(chapterIndex, novel.chapters.length - 1));
    const chapter = novel.chapters[index];
    saveProgress(novel.id, index);
    views.reader.innerHTML = `
      <div class="reader-toolbar">
        <div>
          <button data-back-library>返回书库</button>
          <button data-open-detail="${novel.id}">返回目录</button>
          <button data-prev-chapter="${novel.id}" ${index === 0 ? "disabled" : ""}>上一章</button>
          <button data-next-chapter="${novel.id}" ${index === novel.chapters.length - 1 ? "disabled" : ""}>下一章</button>
        </div>
        <div>
          <button data-theme="paper">纸张</button>
          <button data-theme="green">护眼</button>
          <button data-theme="night">夜间</button>
          <button data-font="-1">A-</button>
          <button data-font="1">A+</button>
        </div>
      </div>
      <article class="reader-page">
        <h2>${escapeHtml(chapter.title)}</h2>
        ${chapter.content.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
      </article>`;
    views.reader.dataset.novelId = novel.id;
    views.reader.dataset.chapterIndex = String(index);
    applyReaderTheme();
    setView("reader");
  }

  async function routeFromHash() {
    const [, type, id, chapter] = window.location.hash.match(/^#(novel|read)\/([^/]+)\/?(\d+)?$/) || [];
    if (!type) {
      setView("library");
      return;
    }
    const novel = getNovel(id);
    if (!novel) {
      setView("library");
      return;
    }
    if (type === "read") {
      if (novel.needsLoad) await loadGutenbergDetail(novel);
      renderReader(novel, Number(chapter || getProgress(id)));
    } else {
      await renderDetail(novel);
    }
  }

  search.addEventListener("input", () => {
    state.query = search.value;
    if (state.source === "gutenberg") {
      clearTimeout(search._timer);
      search._timer = setTimeout(() => loadGutenbergLibrary().catch((error) => {
        grid.innerHTML = `<div class="empty-state">书源搜索失败：${escapeHtml(error.message)}</div>`;
      }), 450);
    } else {
      renderLibrary();
    }
  });
  sort.addEventListener("change", () => {
    state.sort = sort.value;
    renderLibrary();
  });
  genderFilters.addEventListener("click", (event) => {
    const button = event.target.closest("[data-gender]");
    if (!button) return;
    state.gender = button.dataset.gender;
    renderLibrary();
  });
  categoryFilters.addEventListener("click", (event) => {
    const button = event.target.closest("[data-category]");
    if (!button) return;
    state.category = button.dataset.category;
    renderLibrary();
  });
  sourceButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const nextSource = button.dataset.source;
      if (nextSource === state.source) return;
      state.source = nextSource;
      state.gender = "全部";
      state.category = "全部";
      window.location.hash = "";
      if (state.source === "gutenberg") {
        try {
          await loadGutenbergLibrary();
        } catch (error) {
          novels = [];
          syncSourceHeader();
          grid.innerHTML = `<div class="empty-state">书源加载失败：${escapeHtml(error.message)}</div>`;
        }
      } else {
        novels = [...localNovels];
        syncSourceHeader();
        renderLibrary();
      }
      setView("library");
    });
  });
  document.addEventListener("click", (event) => {
    const detail = event.target.closest("[data-open-detail]");
    if (detail) {
      event.preventDefault();
      window.location.hash = `#novel/${detail.dataset.openDetail}`;
      return;
    }
    const read = event.target.closest("[data-read]");
    if (read) {
      event.preventDefault();
      window.location.hash = `#read/${read.dataset.read}/${read.dataset.chapter || 0}`;
      return;
    }
    if (event.target.closest("[data-back-library]")) {
      window.location.hash = "";
      return;
    }
    const prev = event.target.closest("[data-prev-chapter]");
    if (prev) {
      const id = prev.dataset.prevChapter;
      const current = Number(views.reader.dataset.chapterIndex || 0);
      window.location.hash = `#read/${id}/${Math.max(0, current - 1)}`;
      return;
    }
    const next = event.target.closest("[data-next-chapter]");
    if (next) {
      const id = next.dataset.nextChapter;
      const novel = getNovel(id);
      const current = Number(views.reader.dataset.chapterIndex || 0);
      window.location.hash = `#read/${id}/${Math.min(novel.chapters.length - 1, current + 1)}`;
      return;
    }
    const theme = event.target.closest("[data-theme]");
    if (theme) {
      state.readerTheme = theme.dataset.theme;
      localStorage.setItem("novelReaderTheme", state.readerTheme);
      applyReaderTheme();
      return;
    }
    const font = event.target.closest("[data-font]");
    if (font) {
      state.readerSize = Math.max(16, Math.min(26, state.readerSize + Number(font.dataset.font)));
      localStorage.setItem("novelReaderSize", String(state.readerSize));
      applyReaderTheme();
    }
  });
  window.addEventListener("hashchange", () => {
    routeFromHash();
  });
  window.addEventListener("keydown", (event) => {
    if (!views.reader.hidden && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
      const id = views.reader.dataset.novelId;
      const novel = getNovel(id);
      const current = Number(views.reader.dataset.chapterIndex || 0);
      if (event.key === "ArrowLeft" && current > 0) window.location.hash = `#read/${id}/${current - 1}`;
      if (event.key === "ArrowRight" && current < novel.chapters.length - 1) window.location.hash = `#read/${id}/${current + 1}`;
    }
  });

  syncSourceHeader();
  renderLibrary();
  routeFromHash();
})();
