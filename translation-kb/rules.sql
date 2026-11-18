CREATE TABLE rules (id INTEGER PRIMARY KEY, book TEXT NOT NULL, label TEXT NOT NULL, pattern TEXT NOT NULL, advice TEXT NOT NULL, scope TEXT NOT NULL, origin TEXT NOT NULL);
INSERT INTO rules (book,label,pattern,advice,scope,origin) VALUES
('all', 'I am moving', '\bi am moving\b', '神施行作为时可译“我正在动工”或“我正在运行”。', '叙述实际位移时按动作翻译。', '指南三·2'),
('dydi', 'MY Girl', '\bmy girl\b', '我的使女。', '神称呼本书女性记录者或服事者时。', '指南五·3'),
('dydi', 'In Crowd', '\bin crowd\b', '圈内人；MY In Crowd 可作“我的圈内人”。', '本书特定听众群体；合成称呼保留其余成分。', '指南三·6'),
('dydi', 'got a spanking', '\bgot a spanking\b', '受了管教。', '父亲纠正儿女的比喻；实际身体伤害须如实译。', '第401篇／指南三·5'),
('dydi', 'hold on loosely', '\bhold on loosely and don''?t let go\b', '要轻轻地握着，但不要放手。', '保留两动作的张力，原文未写受词时不补。', '第404篇／指南三·6'),
('dydi', 'goodness and mercy', '\bgoodness and mercy shall follow you all the days of your life\b', '你一生一世必有恩惠慈爱随着你。', '此处诗篇式化用；保留人称、数量和修饰。', '第418篇／指南三·6'),
('dydi', 'darkness and gnashing of teeth', '\bdarkness and gnashing of teeth\b', '在那里有黑暗，有哀哭切齿。', '本处审判场景；一般愤怒或咬牙另译。', '第404篇／指南三·6'),
('dydi', 'Glory poured out … all flesh', '\bglory poured out (?:of|on) all flesh\b', '本处用“浇灌在凡有血气的人身上”，保留原文“我的恩惠、我的荣耀”；of/on 疑错按指南注明。', '第003篇该句及相同语境；不可补成“我的灵”。', '第003篇／指南三·7'),
('dydi', 'Oh', '(?:^|[.!?]\s+|[“"])oh\b', '独立感叹语优先用“哦”。', '根据呼语和语气判断。', '指南三·6'),
('dydi', 'fertilizers', '\bfertilizers\b', '本处可作“土壤”。', '仅第401篇学校培育孩子的比喻。', '第401篇／指南三·5'),
('dydi', 'groomed and brainwashed', '\bwas groomed and brainwashed and drank the poison\b', '他经过刻意培养，被洗脑，又喝下毒药。', '原句及相同语境；毒药的含义随上下文判断。', '第395篇／指南三·6'),
('dydi', 'whims of the devil', '\bwhims of the devil\b', '魔鬼的诡计。按疑似 wiles 处理，文末说明依据。', '仅第401篇相应原句与上下文。', '第401篇／指南八·4'),
('dydi', 'fill you will peace', '\bfill you will peace\b', 'will 按 with 的明显笔误处理。', '仅第401篇相应原句与上下文。', '第401篇／指南八·4'),
('dydi', 'better to lose your job or something that is priceless in your eyes', '\bbetter to lose your job or something that is priceless in your eyes\b', '宁可失去工作，也不要失去无价之物。保留文末修正说明。', '仅第401篇相应原句与上下文。', '第401篇／指南八·4'),
('dydi', 'rhinos? christians?', '\brhinos? christians?\b', '有名无实的基督徒。必要时简注政治称呼 RINO 的可能关联。', '仅第401篇相应原句与上下文。', '第401篇／指南八·4'),
('dydi', 'rhinos', '\brhinos\b', '本篇可作“有名无实的共和党人”。必要时简注疑借指 RINO。', '仅第401篇相应原句与上下文。', '第401篇／指南八·4');

INSERT INTO rules (book,label,pattern,advice,scope,origin) VALUES
('lori', 'My fingers never lose their grip', '\bmy fingers never lose their grip\b', '我的手从不松开。', '神在风暴中安慰听者，前句是人抓住神，此句转为神握住人。', '首轮评阅 A／Lori 001'),
('dydi', 'When the going is great', '\bwhen the going is great[, ]+keep your eyes on me\b', '日子顺遂的时候，更要专心仰望我。', '在艰难与顺遂对举的第三次劝勉中用“更要”；普通重复仍须根据上下文判断。', '首轮评阅 B／DYDI 001'),
('dydi', '第030篇第1段', 'a\ major\ global\ event\ is\ getting\ ready\ to\ occur\.\ it\ is\ not\ what\ you\ think\.\ it\ is\ not\ nuclear,\ and\ it\ is\ not\ the\ rapture\ of\ the\ church\.\ this\ final\ move\ will\ prepare\ the\ church\ to\ come\ home,\ turn\ sinners\ into\ saints\ and\ bring\ revival\ on\ a\ global\ scale\.', '一场全球性的重大事件即将发生。却不是你们所想的，不是核事件，也不是教会被提。这最终行动将会预备教会回家，使罪人成为圣徒，又使复兴临到普天之下。', '本篇完整原段的评阅者译例；沿用其语气和人称时核对当前原文。', '首轮评阅 C／DYDI 030 第1段'),
('dydi', '第030篇第2段', 'i\ have\ pretty\ much\ told\ you,\ but\ i\ am\ launching\ a\ surprise\ attack\ on\ the\ enemy\.\ i\ have\ told\ you\ the\ enemy\ will\ soon\ be\ gone,\ and\ they\ absolutely\ will\.\ they\ have\ had\ time\ to\ repent\ and\ it\ is\ time\ for\ me\ to\ move\.', '这事我几乎已经告诉你们了：我要出其不意地攻击仇敌。我曾对你们说，仇敌很快就要消失，这事必要成就。他们已有时间悔改，现在是我兴起行事的时候。', '本篇完整原段的评阅者译例；沿用其语气和人称时核对当前原文。', '首轮评阅 C／DYDI 030 第2段'),
('dydi', '第030篇第3段', 'stay\ close\ to\ me\ in\ the\ coming\ days\ and\ do\ not\ fear\.\ this\ move\ is\ against\ the\ truly\ evil\ non\-repentant\.\ it\ is\ not\ against\ the\ wayward\ who\ will\ return\ home\ to\ me\.', '在将来的日子，你们要亲近我，不要惧怕。我这次出手，是针对那些真正作恶、不肯悔改的人，不是那些迷途、将要归回我这里的人。', '本篇完整原段的评阅者译例；沿用其语气和人称时核对当前原文。', '首轮评阅 C／DYDI 030 第3段'),
('dydi', '第030篇第4段', 'you\ will\ not\ miss\ this\.\ the\ world\ will\ not\ miss\ this,\ and\ you\ will\ be\ rejoicing\ and\ dancing\ in\ the\ streets\.\ eat\ cake\ and\ send\ gifts\ to\ one\ another\.\ your\ preparation\ is\ prayer,\ get\ some\ cake\ and\ pray\ some\ more\.\ walk\ by\ faith\ and\ enjoy\ your\ time\ with\ me\ and\ my\ son\ yeshua\.\ we\ love\ you\ so\.\ spend\ time\ with\ your\ family\ and\ friends\.', '你们不会错过这事，世人也不会错过。那时你们必欢喜快乐，在街上跳舞。你们要吃糕饼，彼此馈送礼物。你们当作的预备，就是祷告；取些糕饼来，再多多地祷告。你们行事为人要凭着信心，与我并我儿耶稣同享时光。我们何等爱你们。你们也要花些时间陪伴家人和朋友。', '本篇完整原段的评阅者译例；沿用其语气和人称时核对当前原文。', '首轮评阅 C／DYDI 030 第4段'),
('dydi', '第030篇第5段', 'the\ show\ is\ ready\ to\ start\.\ i\ love\ you\ with\ an\ everlasting\ heart\.', '大事就要开场。我以永远的心爱你们。', '本篇完整原段的评阅者译例；沿用其语气和人称时核对当前原文。', '首轮评阅 C／DYDI 030 第5段'),
('dydi', 'Eat cake and send gifts', '\beat cake and send gifts to one another\b', '你们要吃糕饼，彼此馈送礼物。', '庆贺时吃糕饼、互赠礼物的场景；单独出现 cake 时按所指食物选择。', '首轮评阅 C／DYDI 030 第4段'),
('dydi', 'The show is ready to start', '\bthe show is ready to start\b', '大事就要开场。', '此处 show 回指上文预告的大事；实际演出按本义翻译。', '首轮评阅 C／DYDI 030 第5段');

INSERT INTO rules (book,label,pattern,advice,scope,origin) VALUES
('all', '异版经文直引', '\b(?:ampc|nkjv)\b', '已引和合本且经节与引文范围相符的，保留既有中文。AMPC、NKJV 等是英文来源标识。审校先核中文经文；遇到实质性版本差异再单独处理，旁引可保留在出处或译注。', '明确引用经文；仅化用时，保留作者的人称、所指和引述范围。', '用户复评／Lori 131、132'),
('lori', 'play ball', '\b(?:play ball|get the ball rolling|get this show on the road)\b', '若后句只是说事情开始，可译“该动手了／该开场了”。若接着描写击球出场，保留棒球意象。', 'Lori 120 与 131 对读。', '编辑审校／Lori 120、124、131'),
('lori', 'checkmate', '\bcheckmate\b', '棋局比喻中可用“走出将死对方的那一步”。', '局势进入决胜时刻；注意汉语“将军将死”的歧义。', '编辑审校／Lori 122、123'),
('all', 'in the natural', '\b(?:in|through) the natural\b', '与属灵之事对举时可作“眼前所见”；与债务免除、人手办事并列时可作“借寻常途径”。', '谈受造世界或自然现象时仍按本义。', '编辑审校／DYDI 425、426、428；Lori 121'),
('dydi', '记录者插话', '\((?:holy spirit shook me|music playing in my head)\)', '保留括号并标明“记录者插语”，再用记录者的第一人称；随后回到原来引语的说话者。', '这两处括注；其他括号须逐处辨认。', '编辑审校／DYDI 425、426'),
('all', '无需害怕', '\byou have nothing to fear\b', '这是安慰，可译“你们没有什么可怕的／用不着害怕”。', '与描述已经无所畏惧、或直接命令不要害怕分辨。', '编辑审校／Lori 122、126、128'),
('all', 'no rhyme or reason', '\bno rhyme or reason\b', '按不明缘由或看不出规律处理。', '普通习语；讨论诗歌韵律时检查字面义。', '编辑审校／Lori 131'),
('dydi', 'come to Jesus Moment', '\bcome to jesus moment\b', '本处指人须正视真相、作出抉择的严肃关头。', '说骗子面临追究时；若正文确为信主、归向耶稣，须保留宗教意义。', '编辑审校／DYDI 428'),
('lori', 'vindicated', '\byou will soon be vindicated\b', '“很快，人们就会知道你们所说的是真的。”', '亲友日后认可听者所言。司法案件要按案情判断。', '编辑审校／Lori 126'),
('all', '持守与时机', '\b(?:you have but a moment|may seem|when you least expect it)\b', '核对临近或已经发生、看似或确实发生。“when you least expect it”可作“在你最意想不到的时候”。', '时间、表象及盼望程度影响译意时。', '编辑审校／Lori 121、123、128');

INSERT INTO rules (book,label,pattern,advice,scope,origin) VALUES
('lori', 'greener pastures and still waters', '\bgreen(?:er)? pastures and still waters\b', '我必领你们到青草地上、可安歇的水边。', '诗篇23:2牧养意象；保留神的第一人称。泛指另谋出路的 greener pastures 另按上下文。', '用户复评／Lori 129'),
('dydi', 'when I close the Red Sea on him', '\bwhen i close the red sea on him\b', '当我使红海的水合拢，淹没他并他一切的邪恶，又除灭所有被他败坏和迷惑的邪恶党羽之时，我必给他毕生致命的一击！', '本篇先写海水合拢，再写淹没、除灭，最后落在主句。其他长句依动作与主从关系定节奏。', '用户复评／DYDI 427');
