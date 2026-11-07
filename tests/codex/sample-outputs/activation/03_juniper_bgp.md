ابدأ بفحص الوضع الحالي؛ **ما تعملش `commit` عادي لتغيير التوجيه وإنت متصل عن بُعد.** هنحتاج نعرف مسار الإدارة ونحضّر رجوع تلقائي قبل التطبيق.

المعلومات المؤكدة: SRX300، Junos 23.4، الـ AS المحلي `65010`، والجار `192.0.2.1` بالـ AS `65020`.

**1. اجمع الحالة الحالية** من operational mode؛ الأوامر دي قراءة فقط:

```text
show interfaces terse
show chassis cluster status
show configuration routing-options | display set
show configuration protocols bgp | display set
show configuration policy-options | display set
show configuration security zones | display set
show configuration interfaces | display set
show configuration firewall | display set
show route 192.0.2.1
show route 0.0.0.0/0 exact
show bgp summary
```

المطلوب تحديد واجهة المزود وعنوانك عليها، وجود BGP أو routing-instance حالي، وأي فلتر ممكن يمنع TCP/179. لو الجهاز مش cluster، رسالة إن الـ cluster غير مفعّل طبيعية.

**2. ثبّت اتفاق التوجيه مع المزود قبل كتابة الإعدادات:**

- هتستقبل **default route فقط** ولا مجموعة prefixes؟ الـ SRX300 موارده محدودة؛ ما تبدأش بـ full Internet table.
- إيه الـ prefixes المسموح لك تعلنها؟ لازم تكون موجودة كمسارات صالحة عندك.
- هل الجار متصل مباشرة، ولا محتاج multihop؟ وهل فيه BGP authentication؟
- العنوان `192.0.2.1` مخصص للأمثلة، والـ ASين private؛ لو دي القيم الفعلية لاتصال إنترنت عام، راجع استخدامها مع المزود.

الإعداد النهائي لازم يحتوي على **import/export policies صريحة تنتهي بـ reject**، وحد لعدد الـ prefixes المتفق عليها. على SRX لازم كمان نراجع السماح بـ BGP في `host-inbound-traffic` والـ firewall filters؛ فتح security policy بين zones وحده مش كفاية للـ BGP المنتهي على الجهاز.

**3. وقت التطبيق لاحقًا، استخدم رجوع تلقائي.** ده ترتيب العمل بعد تجهيز ومراجعة التغيير، مش بلوك تنفّذه دلوقتي:

```text
show | compare
commit check
commit confirmed 10
```

الأخير يفعّل التغيير ويرجّع الإعداد السابق تلقائيًا بعد 10 دقائق لو ما اتأكدش، حتى لو جلسة SSH انقطعت. احتفظ بنسخة من الإعداد الحالي خارج الجهاز، وخلي console أو مسار إدارة بديل متاح لو أمكن.

قبل التأكيد، اختبر:

```text
run show bgp summary
run show route receive-protocol bgp 192.0.2.1
run show route advertising-protocol bgp 192.0.2.1
```

لازم الجلسة تبقى `Established`، والمسارات المستقبلة والمعلنة تطابق الاتفاق، والإنترنت والخدمات الحالية تفضل شغالة. افتح **جلسة SSH جديدة** كمان. بعد نجاح الاختبارات فقط استخدم `commit` للتأكيد؛ **`commit check` أثناء انتظار التأكيد ممكن يؤكد التغيير أيضًا**، فماتستخدموش وقتها لمجرد الفحص.

لو الاختبارات فشلت، سيب المؤقت يرجّع التغيير. وللرجوع يدويًا، راجع `show system commit` وحدد النسخة الصحيحة قبل `rollback <n>` ثم `commit`؛ ما تفترضش إن `rollback 1` دايمًا هي النسخة المطلوبة.

ابعت ناتج الفحص بعد إخفاء أي مفاتيح أو كلمات مرور، ومعاه: **عنوانك وواجهة المزود، داخل للإدارة من أي مسار وهل فيه console بديل، والـ prefixes اللي هتعلنها ونوع المسارات اللي هتستقبلها**. على أساسهم نحدد أقل إضافة لازمة بدون تعارض مع الموجود.