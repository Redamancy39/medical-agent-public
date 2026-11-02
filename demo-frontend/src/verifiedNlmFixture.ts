import type { ClaimReviewItem, EvidenceAnchor, RunOut, SourceItem } from './types.ts'

export interface VerifiedNlmSection {
  id: string
  start: number
  end: number
  text: string
  section: string
  source_spans: Array<{ start: number; end: number; quote: string }>
}

export interface VerifiedNlmDoc {
  id: string
  version: string
  title: string
  url: string
  publisher: string
  jurisdiction: string
  source_language: string
  language: string
  source_sha256: string
  license: string
  license_url: string
  attribution: string
  clinical_review_status: string
  editorial_status: string
  editorial_text: string
  raw: string
  sections: VerifiedNlmSection[]
}

export const VERIFIED_NLM_FIXTURE: Record<string, VerifiedNlmDoc> = {
  "nlm-uacr-test": {
    "id": "nlm-uacr-test",
    "version": "3772202d3291-zh-42e69b95deb8",
    "title": "尿白蛋白肌酐比检测",
    "url": "https://medlineplus.gov/lab-tests/microalbumin-creatinine-ratio/",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "3772202d3291e1828d35291338b1af2ccdbd7e8264959fbc0cdb1ecdc1670946",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "UACR检查肾脏白蛋白漏出\n尿白蛋白肌酐比UACR把尿中白蛋白与肌酐进行比较，可帮助发现异常白蛋白排出和早期肾病。正常肾脏通常只让极少白蛋白进入尿中；损伤时可能更多。糖尿病与高血压属于肾病风险因素，早期肾病可能没有症状。\n英文依据：compares the levels of albumin in your urine to your levels of creatinine.\nEarly kidney disease usually doesn't have any symptoms.\nHave diabetes\nHave high blood pressure\n\nUACR样本与复查\n可以使用随机尿、晨尿或24小时尿等采集方式；具体采样及复查按医护说明。UACR体现白蛋白漏出的信息，不等同于直接测肾小球滤过率；一个结果需要结合其他检查解释，不能直接自行给慢性肾病分期。\n英文依据：A 24-hour urine sample\nA \"random\" or \"spot\" urine sample\n\n",
    "raw": "What is a microalbumin creatinine ratio test?\n\nA microalbumin creatinine ratio urine test checks the levels of the protein albumin in your urine (pee). Abnormal amounts of this protein may be an early sign of kidney disease.\n\nYour kidneys are two organs on either side of your spine near your waist. Filters in your kidneys remove waste and extra water from your blood and gets rid of them through urine. Albumin, however, is not a waste product. It is a common protein found in blood. Therefore, very little, if any, of it should pass into your urine.\n\nIn healthy kidneys, only a trace of albumin, at most, will get through the filters. This trace is often called microalbumin. But if your kidneys are damaged, large amounts of albumin may pass into your urine.\n\nCreatinine, however, often appears in your urine. It is a waste product that comes from daily wear and tear on your muscles. Your kidneys usually get rid of this protein at a steady rate. The microalbumin creatinine ratio test compares the levels of albumin in your urine to your levels of creatinine. This ratio can help your health care provider tell if your body is getting rid of albumin at an increased rate.\n\nOther names: albumin-creatinine ratio; urine albumin; microalbumin, urine; ACR; UACR\n\nWhat is it used for?\n\nA microalbumin creatinine ratio test is most often used to look for signs of kidney disease in people who have a high risk of developing it but don't have symptoms. You're more likely to develop kidney disease if you:\n\n- Have diabetes\n- Have high blood pressure\n- Have a family health history of kidney disease, diabetes, or high blood pressure\n- Have heart disease\n- Are over 50 years old\n- Smoke\n- Have obesity\n\nA microalbumin creatinine ratio test may be used to monitor your kidneys if you have been diagnosed with kidney disease. It can also help your provider see how well any treatment for kidney disease is working.\n\nWhy do I need a microalbumin creatinine ratio test?\n\nEarly kidney disease usually doesn't have any symptoms. So, if you have a high risk for kidney disease, you need a microalbumin creatinine ratio test so you can determine if you have early signs of kidney disease. If you do, treating it early can keep it from getting worse.\n\nBecause diabetes is the most common causes of kidney disease, it is important for anyone with this condition to get tested for kidney disease every year.\n\nIf you have other conditions that increase your risk for getting kidney disease, such as high blood pressure or heart disease, ask your provider how often you need to get tested.\n\nWhat happens during a microalbumin creatinine ratio test?\n\nThere are several ways to collect a urine sample for a microalbumin creatinine ratio test:\n\n- A \"random\" or \"spot\" urine sample means that you collect a single urine sample at any time of the day. You will usually collect this sample at your provider's office or at a medical lab.\n- An early morning or timed urine sample is collected first thing in the morning or after not going to the bathroom for four hours. You'll likely be given a kit and instructions on how to collect your urine at home.\n- A 24-hour urine sample requires you to collect all your urine over a 24-hour period. This test is usually used to follow up on abnormal results from a test on a single sample of urine. A 24-hour urine test is the most accurate way to measure albumin in urine.\n\nFor a random urine sample, a health care professional may give you a cleansing wipe, a small container, and instructions for how to use the \"clean catch\" method to collect your urine sample. It's important to follow these instructions so that germs from your skin don't get into the sample:\n\n- Wash your hands with soap and water and dry them.\n- Open the container without touching the inside.\n- Clean your genital area with the cleansing wipe: For a penis, wipe the entire head (end) of the penis. If you have a foreskin, pull it back first. For a vagina, separate the labia (the folds of skin around the vagina) and wipe the inner sides from front to back.\n- Urinate into the toilet for a few seconds and then stop the flow. Start urinating again, this time into the container. Don't let the container touch your body.\n- Collect at least an ounce or two of urine into the container. The container should have markings to show how much urine is needed.\n- Finish urinating into the toilet.\n- Put the cap on the container and return it as instructed.\n\nFor home collection for an early morning or timed urine sample, the instructions will be about the same as for a random urine sample. Be sure to follow the instructions that come with your collection kit.\n\nFor a 24-hour urine sample, you'll be given a special container to collect your urine over a full day and instructions on how to collect and store your sample. Your provider will tell you what time to start. The test generally includes the following steps:\n\n- To begin, urinate in the toilet as usual. Do not collect this urine. Write down the time you urinated.\n- For the next 24 hours, collect all your urine in the container.\n- During the collection period, store the urine container in a refrigerator or in a cooler with ice.\n- 24 hours after starting the test, try to urinate if you can. This is the last urine collection for the test.\n- Return the container with your urine to your provider's office or the laboratory as instructed.\n\nIf you have hemorrhoids that bleed or are having your menstrual period, tell your provider before your test.\n\nWill I need to do anything to prepare for the test?\n\nBefore providing your urine sample, you may need to avoid:\n\n- Intense exercise. Hard exercise may increase the amount of albumin in your urine for a short time.\n- Eating meat. Meat can affect your creatine levels, so you may be asked not to eat any for a day before your test.\n\nCheck with your provider about how to prepare for your test. Be sure to ask if any medicines or supplements you take could affect your results.\n\nAre there any risks to the test?\n\nThere is no known risk to providing a urine sample for a microalbumin creatinine ratio test.\n\nWhat do the results mean?\n\nIf your microalbumin creatinine ratio shows an abnormal amount of albumin in your urine, you will likely need more tests to confirm your results. That's because temporary increases in albumin levels may be caused by exercise, certain medicines, fever, and inflammation in the body.\n\nUsually, you will have two more tests during the three to six months after your first test. If two out of three tests show abnormal levels of albumin in your urine, you may have early-stage kidney disease.\n\nHigher or increasing amounts of albumin in your urine usually mean you have:\n\n- More serious kidney disease that's likely to get worse faster.\n- A higher risk for developing problems with your heart and blood vessels (vascular diseases).\n\nIf you have higher-than-normal amounts of albumin in your urine, you may need to be tested more often.\n\nSmaller amounts of albumin in your urine don't always mean you have kidney disease. Other conditions that cause inflammation may increase albumin in urine, including:\n\n- Urinary tract infections.\n- Gum infections (periodontitis).\n- Hepatitis.\n\nYour test results may also be affected by your muscle density and your diet, age, and race.\n\nIf you have an abnormal result, your provider will usually order other kidney tests, including a blood test called an estimated glomerular filtration rate (eGFR) test. Talk with your provider about what your test results mean. If you're diagnosed with early kidney disease, there are steps you can take to reduce the amount of albumin in your urine and protect your health.\n\nLearn more about laboratory tests, reference ranges, and understanding results.\n\nIs there anything else I need to know about a microalbumin creatinine ratio?\n\nIt's easy to confuse prealbumin with albumin. Although they sound similar, prealbumin is a different type of protein. A prealbumin test is not part of testing your kidney health.",
    "sections": [
      {
        "id": "9eba6504a040bc563088bb1bd3069f3ba75daa4a6fac13b237033f38023d1571",
        "start": 0,
        "end": 285,
        "text": "UACR检查肾脏白蛋白漏出\n尿白蛋白肌酐比UACR把尿中白蛋白与肌酐进行比较，可帮助发现异常白蛋白排出和早期肾病。正常肾脏通常只让极少白蛋白进入尿中；损伤时可能更多。糖尿病与高血压属于肾病风险因素，早期肾病可能没有症状。\n英文依据：compares the levels of albumin in your urine to your levels of creatinine.\nEarly kidney disease usually doesn't have any symptoms.\nHave diabetes\nHave high blood pressure",
        "section": "UACR检查肾脏白蛋白漏出",
        "source_spans": [
          {
            "start": 991,
            "end": 1065,
            "quote": "compares the levels of albumin in your urine to your levels of creatinine."
          },
          {
            "start": 1965,
            "end": 2020,
            "quote": "Early kidney disease usually doesn't have any symptoms."
          },
          {
            "start": 1508,
            "end": 1521,
            "quote": "Have diabetes"
          },
          {
            "start": 1524,
            "end": 1548,
            "quote": "Have high blood pressure"
          }
        ]
      },
      {
        "id": "9c7108ef855b636ef113377914bc6f747a3253af901d29b36d1389d900885bfd",
        "start": 287,
        "end": 452,
        "text": "UACR样本与复查\n可以使用随机尿、晨尿或24小时尿等采集方式；具体采样及复查按医护说明。UACR体现白蛋白漏出的信息，不等同于直接测肾小球滤过率；一个结果需要结合其他检查解释，不能直接自行给慢性肾病分期。\n英文依据：A 24-hour urine sample\nA \"random\" or \"spot\" urine sample",
        "section": "UACR样本与复查",
        "source_spans": [
          {
            "start": 3134,
            "end": 3156,
            "quote": "A 24-hour urine sample"
          },
          {
            "start": 2729,
            "end": 2762,
            "quote": "A \"random\" or \"spot\" urine sample"
          }
        ]
      }
    ]
  },
  "nlm-gfr-test": {
    "id": "nlm-gfr-test",
    "version": "450e66f03685-zh-6525f8793081",
    "title": "肾小球滤过率检测",
    "url": "https://medlineplus.gov/lab-tests/estimated-glomerular-filtration-rate-egfr-and-gfr-tests/",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "450e66f03685d5548bd2b41de9e0cdf90eef01a040c1067c87f20ff4c1828102",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "eGFR与直接GFR的区别\neGFR是肾小球滤过率的估计，用于了解肾脏过滤废物的能力。医护常以血肌酐等指标结合其他信息估算，某些情况也用胱抑素C。直接测量mGFR需要注入标记物并观察清除，较复杂且不普遍。eGFR不同于尿白蛋白漏出，也不只是血肌酐一个数字。\n英文依据：creatinine levels alone\neGFR may also be calculated using the level of cystatin C\nthis test is complicated and not widely available.\n\n肾脏筛查与结果适用范围\n糖尿病、高血压和家族史等可增加肾病风险，早期肾病常无症状。eGFR用于筛查、诊断辅助或监测；某些特殊体型、肌肉情况和其他疾病可能影响估算可靠性。准备与用药需问医护，不应自行停药，也不能凭单次估算值直接推断病因或制定治疗。\n英文依据：Usually, kidney disease doesn't cause symptoms if it's in an early stage.\nHave diabetes\nHave high blood pressure\ndon't stop taking any medicine unless your provider tells you to.\n\n",
    "raw": "What are estimated glomerular filtration rate (eGFR) and GFR tests?\n\nEstimated glomerular filtration rate (eGFR) and GFR tests check how well your kidneys are working. Your kidneys are two organs on either side of your spine just below your rib cage. They have tiny filters called glomeruli. These filters remove waste and extra water from your blood and get rid of them through your urine (pee).\n\nA GFR test checks how well your kidneys are working directly by measuring the amount of certain waste substances in your blood. This is sometimes called a measured GFR (or mGFR). Health care providers do this by injecting you with certain substances and monitoring how quickly your kidneys can filter it out. However, this test is complicated and not widely available. It's usually only done in certain circumstances, such as if you have extreme obesity or are about to donate a kidney.\n\nBecause mGFR tests aren't common, providers usually use an estimate (or eGFR) to see how well your kidneys are working. To measure your eGFR, providers often start by measuring your creatinine levels. Creatinine is a waste product that comes from normal wear and tear on your muscles. If your kidneys aren't working well, creatinine can build up in your blood.\n\nYour creatinine levels alone, however, can't determine your eGFR. This is because people make different amounts of creatinine, depending on their size, diet, and activity levels. So, to calculate your eGFR, your provider will also consider your:\n\n- Age\n- Weight\n- Height\n- Sex\n\nThis information is put into a mathematical formula, called a GFR calculator, to find your eGFR.\n\neGFR may also be calculated using the level of cystatin C in your blood. This is a protein that many cells in your body make. Unlike your creatinine levels, your cystatin C levels are not affected by muscle size, age, or diet. So some researchers think cystatin C provides a more accurate estimate of GFR than creatinine. In certain cases, creatinine and cystatin levels are both used to calculate eGFR in adults.\n\nOther names: estimated GFR, eGFR, calculated glomerular filtration rate, cGFR\n\nWhat is it used for?\n\nAn eGFR and mGFR test are used to see if your kidneys are filtering waste at a healthy rate. If they filter waste too slowly, it could be a sign that your kidneys have been damaged by kidney disease.\n\neGFR tests are used to:\n\n- Screen for kidney disease in people without symptoms\n- Help diagnose kidney disease in people who have symptoms\n- Help find out how serious kidney disease is\n- Monitor people who are being treated for chronic kidney disease (CKD) or taking medicines that could harm their kidneys\n- Check kidney health before people start certain treatments that could affect their kidneys\n\nIf an eGFR test helps to identify kidney disease early on, you and your provider can take steps to make sure it doesn't get worse.\n\nWhy do I need a GFR test?\n\nOften, your provider will check your eGFR during a routine checkup. They can do this by measuring your creatinine levels during a basic metabolic panel (a test that measures eight different substances in your blood).\n\nYou may also need an eGFR test if you have:\n\n- Kidney disease without symptoms\n- A high risk for kidney disease\n- Symptoms of kidney disease\n\nUsually, kidney disease doesn't cause symptoms if it's in an early stage. Because of this, your provider may want to check your eGFR during a routine exam if they know you have early-stage kidney disease. That way, they can see if it gets worse before you start having symptoms.\n\nYou may be at higher risk for kidney disease if you:\n\n- Have diabetes\n- Have high blood pressure\n- Have a family history of kidney disease, diabetes, or high blood pressure\n- Have heart disease\n- Are over 60 years old\n- Smoke\n- Have obesity\n\nIf you have a condition that increases your risk of kidney disease, ask your provider how often you should get tested.\n\nLater stage kidney disease does cause symptoms. So, you may need an eGFR test if you have:\n\n- Swelling in your legs, feet, ankles, or hands or face\n- Urinating (peeing) more often or less often than usual\n- Dry skin and/or itching\n- Fatigue\n- Muscle cramps\n- Nausea and vomiting\n- Loss of appetite\n\nIn some cases, your provider may measure your cystatin C levels instead of your creatinine levels. They may do this if you:\n\n- Are younger than 18 or over 65\n- Have a lot of muscle mass\n- Have obesity\n- Are pregnant\n\nAn mGFR test that checks your blood is usually only used if:\n\n- Your provider needs a more exact measurement of your creatinine or cystatin C levels. They may need this if you take certain medicines such as a specific type of chemotherapy.\n- You have a health condition that makes an eGFR unreliable. These conditions include severe malnutrition, muscle wasting conditions such as atrophy, and advanced liver disease.\n- You've had a limb amputated. Muscle mass affects your creatinine levels, which are used in an eGFR calculation. So, if you've had a limb amputated, your creatinine levels may appear unhealthy even though they aren't. mGFR testing can give your provider a clearer picture.\n- You're about to donate a kidney. In this case, your provider will want to use mGFR testing because its more exact measurements can tell them if the kidney is working the way it should.\n\nWhat happens during a GFR test?\n\nFor eGFR testing, a health care professional will take a blood sample from a vein in your arm, using a small needle. After the needle is inserted, a small amount of blood will be collected into a test tube or vial. You may feel a little sting when the needle goes in or out. This usually takes less than five minutes.\n\nFor mGFR testing, a health care professional will inject you with a substance called a filtration marker. Your kidneys then filter this filtration marker out of your blood. To see how well your kidneys do this, a health care professional will take a blood sample every 2 to 3 hours. They may also take a sample of your urine (pee).\n\nWill I need to do anything to prepare for these tests?\n\nYour provider will let you know how to prepare for your eGFR test. You may need to fast (not eat or drink) or avoid certain foods, such as meat, for several hours before the test. This is because some foods like meat can affect your eGFR score. Certain medicines can also affect your results. So be sure to tell your provider everything you're taking. But don't stop taking any medicine unless your provider tells you to.\n\nIf you're getting an mGFR test, you may need to fast or avoid certain foods before the test. If your provider wants to test your urine, you may be asked to drink a specific amount of water. Ask your provider if you need to do anything else to prepare for this test.\n\nAre there any risks to the test?\n\nThere is very little risk to having a blood test for an eGFR test. You may have slight pain or bruising at the spot where the needle was put in, but most symptoms go away quickly.\n\nIn some cases, the substances used during an mGFR test can cause an allergic reaction. However, this isn't common.\n\nWhat do the results mean?\n\nYour eGFR results may be reported as a number that shows how much blood your kidneys filter per minute. Your test results may also show your creatinine or cystatin C level.\n\nAsk your provider to explain what your eGFR says about your kidney health. An eGFR isn't a perfect test and may not always reflect kidney damage. It's also possible to have an abnormal result even if you don't have kidney damage. Because eGFR can vary from person to person based on factors like age, body size, and other health conditions, your provider can help you understand how these general ranges apply to you.\n\nIn general:\n\n- An eGFR between 90 and 100 means that you probably don't have kidney disease\n- An eGFR between 60 and 90 means you may have early-stage kidney disease\n- An eGFR between 15 and 60 means that you may have kidney disease\n- An eGFR below 15 means that you may have kidney failure\n\nIf your eGFR is lower than what's normal for you, your provider may order other tests that check your kidney health. These tests may be ordered with an eGFR or to find the cause of an abnormal eGFR result. They include:\n\n- A protein in urine test. Protein in urine is a sign of kidney damage.\n- A microalbumin creatinine ratio test. This test checks for very small amounts of a protein called albumin in a sample of your urine. Albumin in urine may be one of the first signs of kidney disease.\n- A BUN (blood urea nitrogen) test. BUN is a waste product your kidneys remove from blood. The test checks BUN levels in a sample of your blood.\n- An ultrasound or CT scan of your kidneys. This can help your provider see if there are any problems in your urinary system that are common in people with kidney disease.\n\nThe results of an mGFR test are generally the same as those of an eGFR test.\n\nIf you're diagnosed with kidney disease, your provider will explain what you can do to protect your kidneys from more damage and help prevent kidney failure.\n\nLearn more about laboratory tests, reference ranges, and understanding results.",
    "sections": [
      {
        "id": "c95febd6f3b6e9311aeb2800793ad55c5286ba5e0b6a49cbef28bea58f961c82",
        "start": 0,
        "end": 266,
        "text": "eGFR与直接GFR的区别\neGFR是肾小球滤过率的估计，用于了解肾脏过滤废物的能力。医护常以血肌酐等指标结合其他信息估算，某些情况也用胱抑素C。直接测量mGFR需要注入标记物并观察清除，较复杂且不普遍。eGFR不同于尿白蛋白漏出，也不只是血肌酐一个数字。\n英文依据：creatinine levels alone\neGFR may also be calculated using the level of cystatin C\nthis test is complicated and not widely available.",
        "section": "eGFR与直接GFR的区别",
        "source_spans": [
          {
            "start": 1253,
            "end": 1276,
            "quote": "creatinine levels alone"
          },
          {
            "start": 1624,
            "end": 1681,
            "quote": "eGFR may also be calculated using the level of cystatin C"
          },
          {
            "start": 716,
            "end": 766,
            "quote": "this test is complicated and not widely available."
          }
        ]
      },
      {
        "id": "5142c8c0507e43af621fca94978cc540555eaf3db38e8648cbc3f06abb9aaafd",
        "start": 268,
        "end": 574,
        "text": "肾脏筛查与结果适用范围\n糖尿病、高血压和家族史等可增加肾病风险，早期肾病常无症状。eGFR用于筛查、诊断辅助或监测；某些特殊体型、肌肉情况和其他疾病可能影响估算可靠性。准备与用药需问医护，不应自行停药，也不能凭单次估算值直接推断病因或制定治疗。\n英文依据：Usually, kidney disease doesn't cause symptoms if it's in an early stage.\nHave diabetes\nHave high blood pressure\ndon't stop taking any medicine unless your provider tells you to.",
        "section": "肾脏筛查与结果适用范围",
        "source_spans": [
          {
            "start": 3261,
            "end": 3334,
            "quote": "Usually, kidney disease doesn't cause symptoms if it's in an early stage."
          },
          {
            "start": 3597,
            "end": 3610,
            "quote": "Have diabetes"
          },
          {
            "start": 3613,
            "end": 3637,
            "quote": "Have high blood pressure"
          },
          {
            "start": 6396,
            "end": 6461,
            "quote": "don't stop taking any medicine unless your provider tells you to."
          }
        ]
      }
    ]
  },
  "nlm-a1c-test": {
    "id": "nlm-a1c-test",
    "version": "88534028573f-zh-2369744f56c1",
    "title": "糖化血红蛋白HbA1c检测",
    "url": "https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "88534028573f92f5cacdba47c1c63bdd767886bcb5547bb8f1644b935256016a",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "HbA1c表示长期平均血糖\n糖化血红蛋白HbA1c检测反映过去约2–3个月的平均血糖，不是当前这一刻的血糖。血糖与红细胞内血红蛋白结合，检测相应比例。HbA1c可用于筛查或诊断2型糖尿病、糖尿病前期，也可监测控制情况；不用于诊断1型，但可用于其血糖监测。\n英文依据：over the past two to three months.\nThe A1C test isn't used to diagnose type 1 diabetes\nmay be used for monitoring your blood glucose levels.\n\n准备与解释限制\n检测前应告知正在用的药物，不要自行停药。该HbA1c检测页列出的常用范围为正常低于5.7%、前期5.7–6.4%、糖尿病6.5%或更高，但说明这些范围只是指导，个人目标和诊断需结合情况解释，并可能需其他检测。贫血等影响红细胞的情况以及肾衰竭、肝病可能影响HbA1c结果，不能只凭一个结果自行确诊或改变药物。\n英文依据：The ranges are just a guide\nDiabetes: A1C of 6.5% or higher\nsuch as anemia\nKidney failure and liver disease can also affect A1C results.\ndon't stop taking any medicines unless your provider tells you to.\n\n",
    "raw": "What is a hemoglobin A1C (HbA1C) test?\n\nA hemoglobin A1C (HbA1C) test is a blood test that shows your average level of blood glucose, also called blood sugar, over the past two to three months.\n\nGlucose is a type of sugar in your blood that comes from the foods you eat. Your cells use glucose for energy. A hormone called insulin helps glucose get into your cells. If you have diabetes your body doesn't make enough insulin, or your cells don't use it well. As a result, glucose can't get into your cells, so your blood glucose levels increase.\n\nGlucose in your blood sticks to hemoglobin, a protein in your red blood cells. As your blood glucose levels increase, more of your hemoglobin will be coated with glucose. An A1C test measures the percentage of your red blood cells that have glucose-coated hemoglobin.\n\nAn A1C test can show your average glucose level for the past three months because:\n\n- Glucose sticks to hemoglobin for as long as the red blood cells are alive.\n- Red blood cells live about three months.\n\nHigh A1C levels are a sign of high blood glucose from diabetes. Diabetes can cause serious health problems, including heart disease, kidney disease, and nerve damage. But with treatment and lifestyle changes, you can control your blood glucose levels.\n\nOther names: HbA1C, A1C, glycohemoglobin, glycated hemoglobin, glycosylated hemoglobin\n\nWhat is it used for?\n\nYour blood glucose level changes all the time. If you're checking it at home, you are measuring what your blood glucose level is at that time. An A1C test gives you an average level of your blood glucose level over the past two to three months.\n\nAn A1C test may be used to screen for or diagnose:\n\n- Type 2 diabetes. With type 2 diabetes your blood glucose gets too high because your body doesn't make enough insulin or doesn't use insulin well. The glucose then stays in your blood and not enough goes into your cells.\n- Prediabetes. Prediabetes means that your blood glucose levels are higher than normal, but not high enough to be diagnosed as diabetes. Lifestyle changes, such as healthy eating and exercise, may help delay or prevent prediabetes from becoming type 2 diabetes.\n\nIf you have diabetes or prediabetes, an A1C test can help monitor your condition and check how well you've been able to control your blood glucose levels.\n\nThe A1C test isn't used to diagnose type 1 diabetes but may be used for monitoring your blood glucose levels.\n\nWhy do I need an A1C test?\n\nThe Centers for Disease Control (CDC) recommends A1C testing for diabetes and prediabetes if:\n\n- You are over age 45. If your results are normal, your provider will tell you how often you should be tested based on your age and risk factors. If your results show you have prediabetes, you will usually need to be tested every 1 to 2 years. Ask your provider how often to get tested and what you can do to reduce your risk of developing diabetes. If your results show you have diabetes, you should get an A1C test at least twice a year to monitor your condition and treatment.\n- You are under 45 and are more likely to develop diabetes because you: Have prediabetes. Are overweight or have obesity. Have a parent or sibling with type 2 diabetes. Have high blood pressure or high cholesterol levels. Have heart disease or have had a stroke. Are physically active less than 3 times a week. Have had gestational diabetes (diabetes during pregnancy) or given birth to a baby over 9 pounds. Are African American, Hispanic or Latino, American Indian, or an Alaska Native person. Some Pacific Islander and Asian American people also have a higher risk of developing diabetes. Have polycystic ovarian syndrome (PCOS).\n\nYou may also need an A1C test if you have symptoms of diabetes, such as:\n\n- Feeling very thirsty\n- Urinating (peeing) a lot\n- Losing weight without trying\n- Feeling very hungry\n- Blurred vision\n- Numb or tingling hands or feet\n- Fatigue\n- Dry skin\n- Sores that heal slowly\n- Having more infections than usual\n\nWhat happens during an A1C test?\n\nA health care professional will take a blood sample from a vein in your arm, using a small needle. After the needle is inserted, a small amount of blood will be collected into a test tube or vial. You may feel a little sting when the needle goes in or out. This usually takes less than five minutes.\n\nWill I need to do anything to prepare for the test?\n\nCertain medicines such as opioids and some HIV medicines may affect your results, so tell your provider about everything you take. But don't stop taking any medicines unless your provider tells you to. Also, let your health care provider know if you are pregnant, since this may affect your results.\n\nAre there any risks to the test?\n\nThere is very little risk to having a blood test. You may have slight pain or bruising at the spot where the needle was put in, but most symptoms go away quickly.\n\nWhat do the results mean?\n\nA1C results tell you what percentage of your hemoglobin is coated with glucose. The ranges are just a guide to what is normal. What's normal for you depends on your health, age, and other factors. Ask your provider what A1C percentage is healthy for you.\n\nTo diagnose diabetes or prediabetes, the percentages commonly used are:\n\n- Normal: A1C below 5.7%\n- Prediabetes: A1C between 5.7% and 6.4%\n- Diabetes: A1C of 6.5% or higher\n\nProviders often use more than one test to diagnose diabetes. So, if your test result was higher than normal, you may have another A1C test or a different type of diabetes test, usually either a fasting blood glucose test or an oral glucose tolerance test (OGTT).\n\nIf your A1C test was done to monitor your diabetes, talk with your provider about what your test results mean.\n\nLearn more about laboratory tests, reference ranges, and understanding results.\n\nIs there anything else I need to know about an A1C test?\n\nThe A1C test is not used to diagnose gestational diabetes. Also, if you have a condition that affects your red blood cells, such as anemia or another type of blood disorder, an A1C test may not be accurate for diagnosing diabetes. Kidney failure and liver disease can also affect A1C results. In these cases, your provider may recommend different tests to diagnose diabetes and prediabetes.",
    "sections": [
      {
        "id": "26e3b2de1fed61dbc1c309abea983a69bea4e0a3d523d2695302e3bcc54a88c7",
        "start": 0,
        "end": 273,
        "text": "HbA1c表示长期平均血糖\n糖化血红蛋白HbA1c检测反映过去约2–3个月的平均血糖，不是当前这一刻的血糖。血糖与红细胞内血红蛋白结合，检测相应比例。HbA1c可用于筛查或诊断2型糖尿病、糖尿病前期，也可监测控制情况；不用于诊断1型，但可用于其血糖监测。\n英文依据：over the past two to three months.\nThe A1C test isn't used to diagnose type 1 diabetes\nmay be used for monitoring your blood glucose levels.",
        "section": "HbA1c表示长期平均血糖",
        "source_spans": [
          {
            "start": 159,
            "end": 193,
            "quote": "over the past two to three months."
          },
          {
            "start": 2323,
            "end": 2374,
            "quote": "The A1C test isn't used to diagnose type 1 diabetes"
          },
          {
            "start": 2379,
            "end": 2432,
            "quote": "may be used for monitoring your blood glucose levels."
          }
        ]
      },
      {
        "id": "784f41de56811ca3741391817578fd7aa37c4e68a58fdd902b9002ba16f66aa4",
        "start": 275,
        "end": 645,
        "text": "准备与解释限制\n检测前应告知正在用的药物，不要自行停药。该HbA1c检测页列出的常用范围为正常低于5.7%、前期5.7–6.4%、糖尿病6.5%或更高，但说明这些范围只是指导，个人目标和诊断需结合情况解释，并可能需其他检测。贫血等影响红细胞的情况以及肾衰竭、肝病可能影响HbA1c结果，不能只凭一个结果自行确诊或改变药物。\n英文依据：The ranges are just a guide\nDiabetes: A1C of 6.5% or higher\nsuch as anemia\nKidney failure and liver disease can also affect A1C results.\ndon't stop taking any medicines unless your provider tells you to.",
        "section": "准备与解释限制",
        "source_spans": [
          {
            "start": 4975,
            "end": 5002,
            "quote": "The ranges are just a guide"
          },
          {
            "start": 5292,
            "end": 5323,
            "quote": "Diabetes: A1C of 6.5% or higher"
          },
          {
            "start": 5964,
            "end": 5978,
            "quote": "such as anemia"
          },
          {
            "start": 6071,
            "end": 6132,
            "quote": "Kidney failure and liver disease can also affect A1C results."
          },
          {
            "start": 4504,
            "end": 4570,
            "quote": "don't stop taking any medicines unless your provider tells you to."
          }
        ]
      }
    ]
  },
  "nlm-blood-glucose": {
    "id": "nlm-blood-glucose",
    "version": "63abd8911345-zh-3dbde15381d2",
    "title": "血糖与监测",
    "url": "https://medlineplus.gov/bloodglucose.html",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "63abd8911345016893ce97f9057999797fbe53842c91304bbe4feabc19351b7c",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "血糖监测与个体目标\n血糖是血液中的葡萄糖，是能量来源。NLM列出的典型糖尿病管理目标为餐前80–130 mg/dL、开始吃饭后两小时低于180 mg/dL；同时明确年龄、其他健康问题等因素可能使个人目标不同，需要与医疗团队确认，不能把典型范围直接当作个人处方。\n英文依据：Before a meal: 80 to 130 mg/dL\nTwo hours after the start of a meal: Less than 180 mg/dL\nYour blood glucose targets may be different\n\n指尖血糖、CGM与低血糖\n指尖血糖仪测量一小份血液中的葡萄糖；连续血糖监测CGM通常用皮下传感器定期显示变化。监测频率由医疗团队确定。低血糖可快速出现，表现可能有颤抖、出汗、饥饿、头晕或意识混乱。原文对许多糖尿病患者用低于70 mg/dL作为低值例子，也强调个人界限可能不同；低血糖可能危险，需要及时处理。\n英文依据：The sensor measures your glucose level every few minutes.\nFor many people with diabetes\nLow blood glucose can be dangerous and should be treated as soon as possible.\n\n",
    "raw": "What is blood glucose?\n\nBlood glucose, or blood sugar, is the main sugar found in your blood. It is your body's primary source of energy. It comes from the food you eat. Your body breaks down most of that food into glucose and releases it into your bloodstream. When your blood glucose goes up, it signals your pancreas to release insulin. Insulin is a hormone that helps the glucose get into your cells to be used for energy.\n\nWhat is diabetes?\n\nDiabetes is a disease in which your blood glucose levels are too high. When you have diabetes, your body doesn't make enough insulin, can't use it as well as it should, or both. Too much glucose stays in your blood and doesn't reach your cells. Over time, having too much glucose in your blood can cause serious health problems (diabetes complications). So if you have diabetes, it's important to keep your blood glucose levels within your target range.\n\nWhat are blood glucose targets?\n\nIf you have diabetes, your blood glucose target is the range you try to reach as much as possible. The typical targets are:\n\n- Before a meal: 80 to 130 mg/dL\n- Two hours after the start of a meal: Less than 180 mg/dL\n\nYour blood glucose targets may be different, depending on your age, any additional health problems you have, and other factors. Talk with your health care team about the best target range for you.\n\nWhen and how should I check my blood glucose?\n\nIf you have diabetes, you'll likely need to check your blood glucose every day to make sure that your blood glucose numbers are in your target range. Some people may need to check their blood glucose several times a day. Ask your health care team how often you need to check it.\n\nThe most common way to check your blood glucose level at home is with a blood glucose meter. A blood glucose meter measures the amount of glucose in a small sample of blood, usually from your fingertip.\n\nContinuous glucose monitoring (CGM) is another way to check your glucose levels. Most CGM systems use a tiny sensor that is inserted under your skin. The sensor measures your glucose level every few minutes. It can show changes in your glucose level throughout the day and night. A CGM system is especially useful for people who take insulin and have problems with low blood glucose.\n\nYour provider will also check your blood glucose with a blood test called an A1C. It checks your average blood glucose level over the past three months. People with diabetes usually have an A1C test at least twice a year. But you may need the test more often if you aren't meeting your diabetes treatment goals.\n\nWhat happens if my blood glucose level becomes too high?\n\nHigh blood glucose is called hyperglycemia. Symptoms that your blood glucose levels may be too high include:\n\n- Feeling thirsty\n- Feeling tired or weak\n- Headaches\n- Urinating (peeing) often\n- Blurred vision\n\nIf you often have high blood glucose levels or symptoms of high blood glucose, talk with your health care team. You may need a change in your diabetes meal plan, physical activity plan, or diabetes medicines.\n\nHigh blood glucose may also be caused by other conditions that can affect insulin or glucose levels in your blood. These conditions include problems with your pancreas or adrenal glands.\n\nWhat happens if my blood glucose level becomes low for me?\n\nHypoglycemia, also called low blood glucose, happens when your blood glucose level drops below what is healthy for you. For many people with diabetes, this means a blood glucose reading lower than 70 mg/dL. Your number might be different, so check with your health care team to find out what blood glucose level is low for you.\n\nSymptoms of low blood glucose tend to come on quickly. The symptoms can be different for everyone, but they may include:\n\n- Shaking\n- Sweating\n- Nervousness or anxiety\n- Irritability or confusion\n- Dizziness\n- Hunger\n\nLow blood glucose levels can be common in people with type 1 diabetes and people with type 2 diabetes who take certain diabetes medicines. If you think you may have low blood glucose, check your level, even if you don't have symptoms. Low blood glucose can be dangerous and should be treated as soon as possible.\n\nAlthough it's rare, you can still get low blood glucose without having diabetes. The causes can include conditions such as liver disease, kidney disease, and hormone deficiencies (lack of certain hormones). Some medicines, such as certain heart medicines and antibiotics, can also cause it. See your provider to find out the cause of your low blood glucose and how to treat it.\n\nNIH: National Institute of Diabetes and Digestive and Kidney Diseases",
    "sections": [
      {
        "id": "9a6cccaeb913c598849b47d06a5b50ef2e5484e3c22dd313be5af6447a56d4ab",
        "start": 0,
        "end": 267,
        "text": "血糖监测与个体目标\n血糖是血液中的葡萄糖，是能量来源。NLM列出的典型糖尿病管理目标为餐前80–130 mg/dL、开始吃饭后两小时低于180 mg/dL；同时明确年龄、其他健康问题等因素可能使个人目标不同，需要与医疗团队确认，不能把典型范围直接当作个人处方。\n英文依据：Before a meal: 80 to 130 mg/dL\nTwo hours after the start of a meal: Less than 180 mg/dL\nYour blood glucose targets may be different",
        "section": "血糖监测与个体目标",
        "source_spans": [
          {
            "start": 1062,
            "end": 1092,
            "quote": "Before a meal: 80 to 130 mg/dL"
          },
          {
            "start": 1095,
            "end": 1151,
            "quote": "Two hours after the start of a meal: Less than 180 mg/dL"
          },
          {
            "start": 1153,
            "end": 1196,
            "quote": "Your blood glucose targets may be different"
          }
        ]
      },
      {
        "id": "6d1d74f7227c2e089f6003e8666533e02b0a1be3a8fa04f770822320fa89f700",
        "start": 269,
        "end": 593,
        "text": "指尖血糖、CGM与低血糖\n指尖血糖仪测量一小份血液中的葡萄糖；连续血糖监测CGM通常用皮下传感器定期显示变化。监测频率由医疗团队确定。低血糖可快速出现，表现可能有颤抖、出汗、饥饿、头晕或意识混乱。原文对许多糖尿病患者用低于70 mg/dL作为低值例子，也强调个人界限可能不同；低血糖可能危险，需要及时处理。\n英文依据：The sensor measures your glucose level every few minutes.\nFor many people with diabetes\nLow blood glucose can be dangerous and should be treated as soon as possible.",
        "section": "指尖血糖、CGM与低血糖",
        "source_spans": [
          {
            "start": 2032,
            "end": 2089,
            "quote": "The sensor measures your glucose level every few minutes."
          },
          {
            "start": 3425,
            "end": 3454,
            "quote": "For many people with diabetes"
          },
          {
            "start": 4087,
            "end": 4164,
            "quote": "Low blood glucose can be dangerous and should be treated as soon as possible."
          }
        ]
      }
    ]
  },
  "nlm-diabetes-tests": {
    "id": "nlm-diabetes-tests",
    "version": "00eea6f5d7e0-zh-45efb32fab43",
    "title": "糖尿病检测与结果解释",
    "url": "https://medlineplus.gov/lab-tests/diabetes-tests/",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "00eea6f5d7e0c01800693826cf672d4b8630e2745f2117798b563940da2534c9",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "不同糖尿病检测测什么\n空腹血糖反映检测时血糖，口服葡萄糖耐量试验OGTT观察饮糖液后的处理能力，随机血糖可任意时点取血，HbA1c反映过去数月平均血糖。原文说尿糖检测较少用于诊断或监测，血液检测更准确；尿糖高可能仍需血检确认，不能把尿糖当作直接确诊。\n英文依据：Random blood sugar. This test can be taken at any time.\nNo fasting is required for this test.\nUrine tests are not often used to diagnose or monitor diabetes\n\n空腹要求和结果解释\n空腹血糖和OGTT需要空腹；随机血糖与HbA1c通常不需要，具体准备按医护指示。检查可用于筛查、诊断或监测，异常值的意义和是否重复检测由医护解释，不能只根据报告一个数字远程确诊。低血糖极低可出现意识丧失或癫痫，需要及时医疗处理。\n英文依据：No fasting is required for this test.\nNo fasting is required for this test.\nIf it drops very low, you could lose consciousness or have a seizure.\n\n",
    "raw": "What are diabetes tests?\n\nDiabetes, also known as diabetes mellitus, is a disease that affects how your body uses glucose (blood sugar). Glucose is your body's main source of energy. A hormone (a chemical messenger in your bloodstream that controls the actions of certain cells or organs) called insulin helps move glucose from your bloodstream into your cells.\n\nIf you have diabetes, your body can't make insulin or can't use it as well as it should, or both. Too much glucose stays in your blood and doesn't reach your cells. This can cause glucose levels to get too high, which can lead to serious health conditions. These may include heart disease, nerve damage, eye problems, and kidney disease.\n\nYour blood glucose can also drop below what is healthy for you. If it drops very low, you could lose consciousness or have a seizure.\n\nDiabetes tests most often measure glucose levels in your blood to monitor your blood glucose level or see if you have or are at risk for diabetes. Urine tests for diabetes are not used as much since they are not as accurate, and you would need a blood test to diagnose diabetes.\n\nOther names: blood glucose, fasting plasma glucose, FPG, oral glucose tolerance test, OGTT, glucose screening test, glucose in urine test, hemoglobin A1c, random blood sugar, blood sugar, fasting blood sugar (FBS)\n\nWhat are they used for?\n\nDiabetes tests are used to screen, monitor, and/or diagnose the following:\n\n- Type 1 diabetes. If you have type 1 diabetes, your body makes little or no insulin. This disease happens when your immune system attacks and destroys cells that produce insulin. It can develop at any age but most often starts in childhood. People with type 1 diabetes must take daily doses of insulin, either by injection or a special pump.\n- Type 2 diabetes. This is the most common form of diabetes. If you have type 2 diabetes, your body may still be able to make insulin, but your cells don't respond well to insulin and can't easily take up enough glucose from your blood. Type 2 diabetes may be caused by your genes and lifestyle factors, such as being overweight or having obesity. The disease most often occurs in adulthood but is becoming more common in children and teens.\n- Gestational diabetes. This is a form of diabetes that develops during pregnancy.\n- Prediabetes. This is a condition in which your blood glucose levels are higher than what is healthy for you but not high enough to be considered diabetes. But having prediabetes raises your risk of getting type 2 diabetes later on.\n\nWhy do I need a diabetes test?\n\nYou may need testing to monitor your blood glucose level or if you have symptoms of diabetes, such as:\n\n- Increased thirst\n- Frequent urination\n- Increased hunger\n- Fatigue\n- Blurred vision\n- Unexplained weight loss\n- Sores that are slow to heal\n- Numbness or tingling in your feet\n\nSymptoms of type 1 diabetes usually come on quickly and can be severe. Symptoms of type 2 diabetes and prediabetes often develop slowly, even over years.\n\nGestational diabetes doesn't usually cause symptoms in the early stages of your pregnancy, but you will most likely be screened for the condition between 24 and 28 weeks of pregnancy. If testing shows your glucose levels are too high, you will be tested again to confirm the diagnosis.\n\nYou may also need testing if you have certain risk factors for type 2 diabetes. You may be at higher risk for developing it if you:\n\n- Are over 35 years old. The American Diabetes Association recommends diabetes screening for prediabetes and diabetes beginning at age 35 years and older.\n- Have prediabetes.\n- Are overweight or have obesity.\n- Have a family history of diabetes.\n- Have high blood pressure or heart disease.\n- Previously had gestational diabetes.\n- Exercise less than three times a week.\n- Have metabolic dysfunction-associated steatotic liver disease (MASLD).\n- Are an African American, Hispanic or Latino, American Indian, or an Alaska Native.\n\nWhat happens during a diabetes test?\n\nThere are several ways to screen for, monitor, and diagnose diabetes. Most tests involve measuring your blood glucose levels.\n\nTo get a blood sample, a health care professional will take a blood sample from a vein in your arm, using a small needle. After the needle is inserted, a small amount of blood will be collected into a test tube or vial. You may feel a little sting when the needle goes in or out. This usually takes less than five minutes.\n\nThe different types of glucose blood tests include:\n\n- Blood glucose test, also known as fasting blood glucose. Before the test, you will need to fast (not eat or drink) for eight hours before the test. This test is usually done in the morning and is often used as a screening test for diabetes. It may be repeated to confirm a diagnosis.\n- Oral glucose tolerance test (OGTT). This test also requires fasting. When you arrive for your test, a blood sample will be taken. You will then drink a sugary liquid that contains glucose. About two hours later, another blood sample will be taken. This test tells your health care provider how well your body processes sugar. This test may be used to test for gestational diabetes. If you are having this test done during pregnancy, you will have your blood drawn every 30 minutes for two to three hours.\n- Glucose challenge test, also known as the glucose screening test. This test may be used to test for gestational diabetes. You will drink a sugary liquid that contains glucose. A blood sample will be taken one hour later. You do not need to fast for this test. If your blood glucose is too high, your provider may order an oral glucose tolerance test.\n- Random blood sugar. This test can be taken at any time. No fasting is required. This test may be used if you have symptoms of diabetes.\n- Hemoglobin A1c (HbA1c). This test measures the average amount of glucose attached to hemoglobin over the past three months. Hemoglobin is the part of your red blood cells that carries oxygen from your lungs to the rest of your body. No fasting is required for this test.\n\nGlucose may also be measured in your urine.\n\nUrine tests are not often used to diagnose or monitor diabetes since blood tests are more accurate. But a urine test may show if you are at risk for getting the disease. If your glucose in urine levels are too high, then you will probably need a blood test to confirm the diagnosis.\n\nFor a glucose in urine test, your provider may recommend an at-home test kit. The kit will include a test strip that you hold under your stream of urine. The test strip will change colors to show different levels of glucose.\n\nWill I need to do anything to prepare for this test?\n\nYou will need to fast (not eat or drink) for a blood glucose and an oral glucose tolerance test.\n\nYou don't need any special preparations for a random blood sugar test, glucose challenge test, hemoglobin A1c test, or glucose in urine test.\n\nAre there any risks to this test?\n\nThere is very little risk to having a blood test. There may be slight pain or bruising at the spot where the needle was put in, but most symptoms go away quickly.\n\nThere is no risk to having a urine test.\n\nWhat do the results mean?\n\nDepending on the type of test or tests you had, your results may show one of the following:\n\n- Your glucose is at a healthy level for you. This means you probably are not at risk for or do not have diabetes.\n- Prediabetes.This means you have glucose levels that are higher than what is healthy for you and may be at risk of getting diabetes.\n- Type 1 or type 2 diabetes.\n- Gestational diabetes.\n\nIf you have been diagnosed with type 1 diabetes, talk to your provider about how to best manage the disease. There is no cure for type 1 diabetes, but it may be controlled with regular glucose monitoring and taking insulin.\n\nIf you've been diagnosed with prediabetes or type 2 diabetes, your condition may be managed or even reversed by taking diabetes medicines and making lifestyle changes. These include eating a healthy diet, losing weight, and increasing exercise.\n\nIf you've been diagnosed with gestational diabetes, you may be able to lower your glucose levels by eating a healthy diet and getting regular exercise. But be sure to talk to your provider about treatment options. Most of the time, gestational diabetes goes away after giving birth. But you will be at higher risk for developing type 2 diabetes in the future.\n\nIf you have other questions about your diabetes diagnosis or treatment, talk to your provider.\n\nLearn more about laboratory tests, reference ranges, and understanding results.\n\nIs there anything else I need to know about diabetes testing?\n\nIf you've been diagnosed with type 1 diabetes, you will need to monitor your blood glucose levels daily, often several times a day. Your provider can recommend a kit you can use at home. Most kits include a lancet, a device that pricks your finger. You will use this to collect a drop of blood for testing. There are some newer kits available that don't require pricking your finger. If you are pregnant and have gestational diabetes, you may also need to monitor your glucose levels in this way.\n\nPeople with type 2 diabetes must also check their blood sugar regularly. If you have type 2 diabetes, talk to your provider about how often it should be checked.\n\nPeople with type 2 diabetes may also need to have their insulin levels checked regularly. Insulin plays a key role in keeping glucose at the right levels. An insulin in blood test is done at a provider's office.",
    "sections": [
      {
        "id": "b286bdb501fb296a0c9a1061af3949ef36cee314edb6efbc4eb5c8e6f5b34fa3",
        "start": 0,
        "end": 287,
        "text": "不同糖尿病检测测什么\n空腹血糖反映检测时血糖，口服葡萄糖耐量试验OGTT观察饮糖液后的处理能力，随机血糖可任意时点取血，HbA1c反映过去数月平均血糖。原文说尿糖检测较少用于诊断或监测，血液检测更准确；尿糖高可能仍需血检确认，不能把尿糖当作直接确诊。\n英文依据：Random blood sugar. This test can be taken at any time.\nNo fasting is required for this test.\nUrine tests are not often used to diagnose or monitor diabetes",
        "section": "不同糖尿病检测测什么",
        "source_spans": [
          {
            "start": 5646,
            "end": 5701,
            "quote": "Random blood sugar. This test can be taken at any time."
          },
          {
            "start": 6017,
            "end": 6054,
            "quote": "No fasting is required for this test."
          },
          {
            "start": 6101,
            "end": 6163,
            "quote": "Urine tests are not often used to diagnose or monitor diabetes"
          }
        ]
      },
      {
        "id": "fc9127cc166c1d78c56f5a11623bd28bd8f4b31c39977ff5fca1f93f4234d30c",
        "start": 289,
        "end": 564,
        "text": "空腹要求和结果解释\n空腹血糖和OGTT需要空腹；随机血糖与HbA1c通常不需要，具体准备按医护指示。检查可用于筛查、诊断或监测，异常值的意义和是否重复检测由医护解释，不能只根据报告一个数字远程确诊。低血糖极低可出现意识丧失或癫痫，需要及时医疗处理。\n英文依据：No fasting is required for this test.\nNo fasting is required for this test.\nIf it drops very low, you could lose consciousness or have a seizure.",
        "section": "空腹要求和结果解释",
        "source_spans": [
          {
            "start": 6017,
            "end": 6054,
            "quote": "No fasting is required for this test."
          },
          {
            "start": 6017,
            "end": 6054,
            "quote": "No fasting is required for this test."
          },
          {
            "start": 766,
            "end": 835,
            "quote": "If it drops very low, you could lose consciousness or have a seizure."
          }
        ]
      }
    ]
  },
  "nlm-bp-medicines": {
    "id": "nlm-bp-medicines",
    "version": "2686229dca08-zh-21b243a99613",
    "title": "降压药物的一般知识",
    "url": "https://medlineplus.gov/bloodpressuremedicines.html",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "2686229dca0816049a1c687b4ad1e0ee381355f7f4e53bce2ed8c72e24336504",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "生活方式与降压药的关系\n减重、运动、减钠、管理压力、避免烟酒和足够睡眠可帮助血压管理。若生活方式不足以控制血压，医护人员可能开降压药。服药时仍需保持健康生活方式，不能把生活方式与药物当成只能选一个。\n英文依据：your health care provider may prescribe blood pressure medicines.\nit is still important to keep up with your healthy lifestyle changes.\n\n降压药机制的一般解释\n常用降压药机制不同：ACE抑制剂与ARB减少血管狭窄，钙通道阻滞剂帮助血管放松，利尿剂排出多余水和钠。β阻滞剂可减慢心率和减弱心脏收缩，资料指出通常作为后备或伴有某些其他情况时使用。某些人需要联合用药；此处不提供个体选药、剂量或自行停药方案。\n英文依据：Beta blockers are typically used only as a backup option\nDiuretics remove extra water and sodium\ntwo or more medicines work better than one\n\n",
    "raw": "What is high blood pressure?\n\nHigh blood pressure, also called hypertension, is when blood puts too much pressure against the walls of your arteries. Almost half of American adults have high blood pressure, usually with no symptoms. But it can cause serious problems such as stroke, heart failure, heart attack, and kidney disease.\n\nWhat lifestyle changes can help lower high blood pressure?\n\nHealthy lifestyle changes can help reduce high blood pressure:\n\n- Losing weight\n- Being physically active\n- Managing stress\n- Reducing sodium in your diet\n- Avoiding alcohol, tobacco, and illegal drugs\n- Getting enough sleep\n\nWhat if lifestyle changes alone cannot lower blood pressure?\n\nSometimes lifestyle changes alone cannot control or lower your high blood pressure. In that case, your health care provider may prescribe blood pressure medicines.\n\nHow do blood pressure medicines work?\n\nThe most commonly used blood pressure medicines work in different ways to lower blood pressure:\n\n- Angiotensin-converting enzyme (ACE) inhibitors and angiotensin II receptor blockers (ARBs) keep your blood vessels from narrowing as much and allows blood to move through them with less pressure.\n- Beta blockers help your heart beat slower and with less force. This means that your heart pumps less blood through your blood vessels. Beta blockers are typically used only as a backup option or if you also have certain other conditions.\n- Calcium channel blockers prevent calcium from entering the muscle cells of your heart and blood vessels. This allows the blood vessels to relax.\n- Diuretics remove extra water and sodium (salt) from your body. This lowers the amount of fluid in your blood. Diuretics are often used with other high blood pressure medicines, sometimes in one combined pill.\n\nOften, two or more medicines work better than one. If these medicines do not lower your blood pressure enough, your provider may suggest that you take another type of blood pressure medicine.\n\nWhile taking the medicines, it is still important to keep up with your healthy lifestyle changes. Doing both helps keep blood pressure lower than lifestyle changes or medicines alone.\n\nNIH: National Heart, Lung, and Blood Institute",
    "sections": [
      {
        "id": "b23ace4766e64c613f622e35269e79202eaed13963f803df23872197a102ab19",
        "start": 0,
        "end": 240,
        "text": "生活方式与降压药的关系\n减重、运动、减钠、管理压力、避免烟酒和足够睡眠可帮助血压管理。若生活方式不足以控制血压，医护人员可能开降压药。服药时仍需保持健康生活方式，不能把生活方式与药物当成只能选一个。\n英文依据：your health care provider may prescribe blood pressure medicines.\nit is still important to keep up with your healthy lifestyle changes.",
        "section": "生活方式与降压药的关系",
        "source_spans": [
          {
            "start": 779,
            "end": 844,
            "quote": "your health care provider may prescribe blood pressure medicines."
          },
          {
            "start": 2000,
            "end": 2069,
            "quote": "it is still important to keep up with your healthy lifestyle changes."
          }
        ]
      },
      {
        "id": "ae4d15ded7984b724e876ea49160c05ff184d9c341649a60008990cef06bbcaf",
        "start": 242,
        "end": 519,
        "text": "降压药机制的一般解释\n常用降压药机制不同：ACE抑制剂与ARB减少血管狭窄，钙通道阻滞剂帮助血管放松，利尿剂排出多余水和钠。β阻滞剂可减慢心率和减弱心脏收缩，资料指出通常作为后备或伴有某些其他情况时使用。某些人需要联合用药；此处不提供个体选药、剂量或自行停药方案。\n英文依据：Beta blockers are typically used only as a backup option\nDiuretics remove extra water and sodium\ntwo or more medicines work better than one",
        "section": "降压药机制的一般解释",
        "source_spans": [
          {
            "start": 1317,
            "end": 1373,
            "quote": "Beta blockers are typically used only as a backup option"
          },
          {
            "start": 1569,
            "end": 1608,
            "quote": "Diuretics remove extra water and sodium"
          },
          {
            "start": 1786,
            "end": 1828,
            "quote": "two or more medicines work better than one"
          }
        ]
      }
    ]
  },
  "nlm-hypertension": {
    "id": "nlm-hypertension",
    "version": "6ef444154364-zh-ef835d098111",
    "title": "高血压基础知识",
    "url": "https://medlineplus.gov/highbloodpressure.html",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "6ef444154364630f65a7934b794d754cff2a841ba77becaee2995afac4245dba",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "血压两个数的含义\n血压是血液对动脉壁的压力。收缩压是心脏搏动时的压力，舒张压是心脏在两次搏动之间休息时的压力；通常第一个数是收缩压，第二个是舒张压。120/80的例子表示收缩压120、舒张压80。\n英文依据：This is called systolic pressure.\nThis is called diastolic pressure.\n120/80 means a systolic of 120 and a diastolic of 80.\n\n高血压判断与长期影响\n高血压通常没有症状，不能仅凭有无头痛判断。NLM资料指出，医护人员在不同就诊时点取得两次或更多读数后判断。其美国来源的表格把130–139或80–89列为1期、140或更高或90或更高列为2期；这是该资料的分类，不是所有地区的统一诊断标准。原发性高血压最常见并随时间发展；继发性可能由其他健康状况或药物引起。长期偏高可增加心脏、脑卒中和肾脏疾病风险；治疗方案由医护人员制定。\n英文依据：High blood pressure usually has no symptoms.\ntwo or more readings at separate appointments\nHigh Blood Pressure Stage 1 | 130 - 139 | or | 80 - 89\nheart attack, stroke, heart failure, and kidney failure\nPrimary, or essential, high blood pressure.\nThis is caused by another medical condition or use of certain medicines.\n\n",
    "raw": "What is blood pressure?\n\nBlood pressure is the force of your blood pushing against the walls of your arteries. Each time your heart beats, it pumps blood into the arteries. Your blood pressure is highest when your heart beats, pumping the blood. This is called systolic pressure. When your heart is at rest, between beats, your blood pressure falls. This is called diastolic pressure.\n\nYour blood pressure reading uses these two numbers. Usually the systolic number comes before or above the diastolic number. For example, 120/80 means a systolic of 120 and a diastolic of 80.\n\nHow is high blood pressure diagnosed?\n\nHigh blood pressure usually has no symptoms. So the only way to find out if you have it is to get regular blood pressure checks from your health care provider. Your provider will use a gauge, a stethoscope or electronic sensor, and a blood pressure cuff. They will take two or more readings at separate appointments before making a diagnosis.\n\nBlood Pressure Category | Systolic Blood Pressure |  | Diastolic Blood Pressure\nNormal | Less than 120 | and | Less than 80\nElevated | 120 - 129 | and | Less than 80\nHigh Blood Pressure Stage 1 | 130 - 139 | or | 80 - 89\nHigh Blood Pressure Stage 2 | 140 or higher | or | 90 or higher\nHypertensive Crisis (dangerously high blood pressure - seek medical care right away) | Higher than 180 | and | Higher than 120\n\nFor children and teens, the health care provider compares the blood pressure reading to what is normal for other kids who are the same age, height, and sex.\n\nWhat are the different types of high blood pressure?\n\nThere are two main types of high blood pressure:\n\n- Primary, or essential, high blood pressure. This is the most common type of high blood pressure. For most people who get this kind of blood pressure, it develops over time as you get older.\n- Secondary high blood pressure. This is caused by another medical condition or use of certain medicines. It usually gets better after you treat that condition or stop taking the medicines that are causing it.\n\nWhy do I need to worry about high blood pressure?\n\nWhen your blood pressure stays high over time, it causes the heart to pump harder and work overtime, possibly leading to serious health problems such as heart attack, stroke, heart failure, and kidney failure.\n\nWhat are the treatments for high blood pressure?\n\nTreatments for high blood pressure include heart-healthy lifestyle changes and medicines.\n\nYou will work with your provider to come up with a treatment plan. It may include only the lifestyle changes. These changes, such as heart-healthy eating and exercise, can be very effective. But sometimes the changes do not control or lower your high blood pressure. Then you may need to take medicine. There are different types of blood pressure medicines. Some people need to take more than one type.\n\nIf your high blood pressure is caused by another medical condition or medicine, treating that condition or stopping the medicine may lower your blood pressure.\n\nNIH: National Heart, Lung, and Blood Institute",
    "sections": [
      {
        "id": "ac1a0537a3ba8932f1b581a0ade448c6392dcbdf8d169ba64bd698b52a5c46a3",
        "start": 0,
        "end": 226,
        "text": "血压两个数的含义\n血压是血液对动脉壁的压力。收缩压是心脏搏动时的压力，舒张压是心脏在两次搏动之间休息时的压力；通常第一个数是收缩压，第二个是舒张压。120/80的例子表示收缩压120、舒张压80。\n英文依据：This is called systolic pressure.\nThis is called diastolic pressure.\n120/80 means a systolic of 120 and a diastolic of 80.",
        "section": "血压两个数的含义",
        "source_spans": [
          {
            "start": 246,
            "end": 279,
            "quote": "This is called systolic pressure."
          },
          {
            "start": 350,
            "end": 384,
            "quote": "This is called diastolic pressure."
          },
          {
            "start": 523,
            "end": 576,
            "quote": "120/80 means a systolic of 120 and a diastolic of 80."
          }
        ]
      },
      {
        "id": "1df5ec9f8dcfbaa8bc79c427bce84de4eab02d5ef1958e6fc1d510d9f8701f14",
        "start": 228,
        "end": 750,
        "text": "高血压判断与长期影响\n高血压通常没有症状，不能仅凭有无头痛判断。NLM资料指出，医护人员在不同就诊时点取得两次或更多读数后判断。其美国来源的表格把130–139或80–89列为1期、140或更高或90或更高列为2期；这是该资料的分类，不是所有地区的统一诊断标准。原发性高血压最常见并随时间发展；继发性可能由其他健康状况或药物引起。长期偏高可增加心脏、脑卒中和肾脏疾病风险；治疗方案由医护人员制定。\n英文依据：High blood pressure usually has no symptoms.\ntwo or more readings at separate appointments\nHigh Blood Pressure Stage 1 | 130 - 139 | or | 80 - 89\nheart attack, stroke, heart failure, and kidney failure\nPrimary, or essential, high blood pressure.\nThis is caused by another medical condition or use of certain medicines.",
        "section": "高血压判断与长期影响",
        "source_spans": [
          {
            "start": 617,
            "end": 661,
            "quote": "High blood pressure usually has no symptoms."
          },
          {
            "start": 887,
            "end": 932,
            "quote": "two or more readings at separate appointments"
          },
          {
            "start": 1127,
            "end": 1181,
            "quote": "High Blood Pressure Stage 1 | 130 - 139 | or | 80 - 89"
          },
          {
            "start": 2243,
            "end": 2298,
            "quote": "heart attack, stroke, heart failure, and kidney failure"
          },
          {
            "start": 1638,
            "end": 1681,
            "quote": "Primary, or essential, high blood pressure."
          },
          {
            "start": 1861,
            "end": 1933,
            "quote": "This is caused by another medical condition or use of certain medicines."
          }
        ]
      }
    ]
  },
  "nlm-bp-test": {
    "id": "nlm-bp-test",
    "version": "3605f16f26b8-zh-1123b25addaa",
    "title": "血压测量",
    "url": "https://medlineplus.gov/lab-tests/measuring-blood-pressure/",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "3605f16f26b8d7e9b90bc28b81899c1087f316e5e7b09d78aff92f295c6c3d75",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "测量条件与准备\n血压可能随休息或运动、咖啡因、酒精、烟草、年龄、药物和姿势改变。NLM测量资料要求测量前至少30分钟避免运动、酒精、烟草及含咖啡因饮食，并在检查前排空膀胱。测量时坐下，双脚平放，手臂与心脏同高；袖带收紧可能短暂不适。\n英文依据：at least 30 minutes\nmake sure to go to the bathroom before the test.\nyour arm is level with your heart\n\n读数解释不是一次确诊\n血压单位是毫米汞柱mm Hg。医护人员通常结合不同日期两次或以上偏高读数、持续变化、个人与家族病史及症状进行判断。一次运动后或含咖啡因后的读数不应由助手直接确诊。原文危急高血压表格要求立即医疗帮助；血压很高伴严重不适时不应等待常规知识解释。\n英文依据：Blood pressure is measured in millimeters of mercury\ntwo or more high blood pressure readings on different days\nyour medical and family history\nseek medical care right away\n\n",
    "raw": "What is a blood pressure measurement?\n\nEach time your heart beats, it pumps blood into your arteries (the blood vessels that carry blood from your heart to the tissues and organs in your body). A blood pressure measurement is a test that measures the force (pressure) in your arteries as your heart pumps. Blood pressure is measured as two numbers:\n\n- Systolic blood pressure (the first and higher number) measures pressure inside your arteries when your heart beats.\n- Diastolic blood pressure (the second and lower number) measures the pressure inside the artery when your heart rests between beats.\n\nFor example, a blood pressure reading of 120/80 means a systolic of 120 and a diastolic of 80.\n\nMany things can change your blood pressure. It can increase or decrease based on:\n\n- Whether you're resting or exercising\n- If you eat or drink foods with caffeine, alcohol, or tobacco\n- Your age\n- If you're taking certain medicines\n- Your position, such as whether you're sitting, lying down, or standing\n\nIf your blood pressure is high on several different measurements on different days, you might have high blood pressure, also known as hypertension. Around half of American adults have high blood pressure. It increases the risk of life-threatening conditions, including heart attack and stroke. But high blood pressure rarely causes symptoms. A blood pressure measurement helps diagnose high blood pressure early, so it may be treated before it leads to serious complications.\n\nOther names: blood pressure reading, blood pressure test, blood pressure screening, sphygmomanometry\n\nWhat is it used for?\n\nA blood pressure measurement is most often used to diagnose high blood pressure.\n\nBlood pressure that's too low, known as hypotension, is much less common. But you may get tested for low blood pressure if you have certain symptoms. Unlike high blood pressure, low blood pressure usually causes symptoms. These include:\n\n- Dizziness or lightheadedness\n- Nausea\n- Cold, sweaty skin\n- Pale skin\n- Fainting\n- Weakness\n\nWhy do I need a blood pressure test?\n\nA blood pressure measurement is often included as part of a regular checkup. Everyone age 3 or older should have their blood pressure checked by their provider at least once a year.\n\nIf you have high blood pressure or are at higher risk for it, you may need testing more often. You may be at higher risk if you:\n\n- Are 40 years old or older.\n- Are overweight or have obesity.\n- Have a family history of heart disease or diabetes.\n- Have a family history of high blood pressure.\n- Take birth control pills or other medicines that can increase your blood pressure.\n- Are Black/African American. Black/African Americans are more likely than other racial and ethnic groups to have high blood pressure.\n\nYour provider can tell you how often you should get your blood pressure checked.\n\nYou may also need to have your blood pressure checked:\n\n- To see how well your blood pressure medicine is working (if you have high blood pressure)\n- If you are being treated in the hospital\n- To check if it's safe for you to have a medical or surgical procedure\n- To check if it's safe for you to play sports or do other strenuous activities or jobs\n- If you have symptoms of low blood pressure\n\nWhat happens during a blood pressure test?\n\nA blood pressure test includes the following steps:\n\n- You will sit in a chair with your feet flat on the floor.\n- You will rest your arm on a table or other surface, so your arm is level with your heart. You may be asked to roll up your sleeve.\n- Your health care provider will wrap a blood pressure cuff around your arm. A blood pressure cuff is a strap-like device. It should fit snugly around your upper arm, with the bottom edge placed just above your elbow.\n- Your provider will inflate the blood pressure cuff using a small hand pump or by pressing a button on an automated device.\n- Your provider will measure the pressure manually (by hand) or with an automated device. If done manually, they will place a stethoscope over the major artery (brachial artery) in your upper arm and elbow joint to listen to the blood flow and pulse as the cuff inflates and deflates. If using an automated device, the blood pressure cuff automatically inflates, deflates, and measures pressure.\n- As the blood pressure cuff inflates, you'll feel it tighten around your arm. This blocks the blood flow in that part of your arm for a short time.\n- Your provider will then open a valve on the cuff to slowly release air. As the cuff deflates, blood flow will start again in your arm.\n- As the pressure falls, a measurement is taken when the sound of blood pulsing is first heard. This is the systolic pressure.\n- As the air continues to be let out, the blood pulsing sound will start to go away. When it completely stops, another measurement is taken. This is the diastolic pressure.\n\nThis test only takes about one minute to complete.\n\nYour provider may also ask to take your blood pressure while you stand or lie down. They may also want to repeat the blood pressure measurement on your other arm.\n\nWill I need to do anything to prepare for the test?\n\nSeveral things can increase your blood pressure measurement. Tell your provider if you take any medicines, since some medicines may affect your results.\n\nTo get a more accurate blood pressure measurement, avoid these things for at least 30 minutes before having your blood pressure taken:\n\n- Exercise\n- Alcohol\n- Tobacco products\n- Food or drinks containing caffeine\n\nAlso, make sure to go to the bathroom before the test.\n\nAre there any risks to the test?\n\nYou may have a little discomfort when the blood pressure cuff inflates and squeezes your arm. But this feeling only lasts for a few seconds.\n\nWhat do the results mean?\n\nYour results, also known as a blood pressure reading, will contain two numbers. The top or first number is the systolic pressure. The bottom or second number is the diastolic pressure. Blood pressure readings are also labeled by categories, ranging from normal to crisis. Blood pressure is measured in millimeters of mercury (mm Hg).\n\nYour reading may show your blood pressure is:\n\nBlood Pressure Category | Systolic Blood Pressure |  | Diastolic Blood Pressure\nNormal | Less than 120 | and | Less than 80\nElevated | 120 - 129 | and | Less than 80\nHigh Blood Pressure Stage 1 | 130 - 139 | or | 80 - 89\nHigh Blood Pressure Stage 2 | 140 or higher | or | 90 or higher\nHypertensive Crisis (dangerously high blood pressure - seek medical care right away | Higher than 180 | and | Higher than 120\n\nYour blood pressure measurement can go up and down. Your provider will only usually diagnose you with high blood pressure if you have two or more high blood pressure readings on different days. They may also consider your blood pressure readings over a period of time, your medical and family history, and if you have other symptoms before diagnosing you with high blood pressure.\n\nIf your child is younger than 13, your provider will compare their blood pressure readings with what is common for children the same age, sex, and height.\n\nIf you've been diagnosed with high blood pressure, your provider may recommend:\n\n- Lifestyle changes and/or medicines to control your blood pressure.\n- You to regularly check your blood pressure at home with an automated blood pressure monitor. An at-home blood pressure monitor usually includes a blood pressure cuff and a digital device to record and display blood pressure readings.\n\nAt-home blood pressure monitoring is not a replacement for regular visits with your provider. But it can provide important information, such as whether your treatment is working or if your condition may have gotten worse.\n\nAlso, home monitoring may make the test less stressful. Many people get nervous about getting their blood pressure taken at a provider's office. This is called \"white coat syndrome.\" It can cause a temporary rise in blood pressure, making the results less accurate.\n\nTo get the most accurate results when taking your blood pressure at home:\n\n- Make sure the blood pressure cuff fits snugly but isn't too small.\n- Use a blood pressure cuff that goes around your upper arm. It is more accurate than the ones that measure on your wrist or finger.\n- Take your blood pressure at the same time of day each time.\n- Rest in the chair for about five minutes before taking your blood pressure.\n- Sit up straight with your legs uncrossed and your feet flat on the floor.\n\nSeek immediate medical attention or call 911 if your blood pressure is over 180/120 mmHg, you have chest pain, shortness of breath, back pain, numbness or weakness, trouble speaking, or vision changes.\n\nFor more information about home monitoring of blood pressure, talk to your provider.\n\nIf you were tested for low blood pressure, a blood pressure reading of 90 systolic, 60 diastolic (90/60 mmHg) or lower is considered abnormal. Treatments for low blood pressure may include medicines and certain dietary changes.\n\nSeek immediate medical attention or call 911 if you have symptoms of extremely low blood pressure, such as confusion, a weak and rapid pulse, or cold skin.\n\nIs there anything else I need to know about a blood pressure measurement?\n\nIf you were diagnosed with high blood pressure, your provider may recommend some lifestyle changes such as:\n\n- Getting regular physical activity. Staying active can help lower your blood pressure and also help manage your weight. Check with your provider before beginning an exercise program.\n- Being at a healthy weight. Losing as little as 5 pounds can lower your blood pressure if you are overweight.\n- Eating a healthy diet that includes fruits, vegetables, and whole grains. Limit foods high in saturated fat and total fat. The DASH eating plan is a heart-healthy style of eating.\n- Reducing salt in your diet. Most adults and children over age 14 should have less than 2,300 mg of salt per day.\n- Limiting alcohol use. Talk to your provider about how much alcohol you drink. They may recommend that you reduce the amount of alcohol you drink or that you stop drinking alcohol.\n- Quitting smoking (if you smoke).\n- Managing stress.\n- Getting enough good-quality sleep.",
    "sections": [
      {
        "id": "45fb8b6431d80feb53ef2a8cc496277b76bb4d16c77a9d7a84df0c2be40c0990",
        "start": 0,
        "end": 224,
        "text": "测量条件与准备\n血压可能随休息或运动、咖啡因、酒精、烟草、年龄、药物和姿势改变。NLM测量资料要求测量前至少30分钟避免运动、酒精、烟草及含咖啡因饮食，并在检查前排空膀胱。测量时坐下，双脚平放，手臂与心脏同高；袖带收紧可能短暂不适。\n英文依据：at least 30 minutes\nmake sure to go to the bathroom before the test.\nyour arm is level with your heart",
        "section": "测量条件与准备",
        "source_spans": [
          {
            "start": 5351,
            "end": 5370,
            "quote": "at least 30 minutes"
          },
          {
            "start": 5497,
            "end": 5545,
            "quote": "make sure to go to the bathroom before the test."
          },
          {
            "start": 3452,
            "end": 3485,
            "quote": "your arm is level with your heart"
          }
        ]
      },
      {
        "id": "16db276a7003701deb5fde2af332ec969774cd74cea315e3b5f403be39dea66a",
        "start": 226,
        "end": 535,
        "text": "读数解释不是一次确诊\n血压单位是毫米汞柱mm Hg。医护人员通常结合不同日期两次或以上偏高读数、持续变化、个人与家族病史及症状进行判断。一次运动后或含咖啡因后的读数不应由助手直接确诊。原文危急高血压表格要求立即医疗帮助；血压很高伴严重不适时不应等待常规知识解释。\n英文依据：Blood pressure is measured in millimeters of mercury\ntwo or more high blood pressure readings on different days\nyour medical and family history\nseek medical care right away",
        "section": "读数解释不是一次确诊",
        "source_spans": [
          {
            "start": 6022,
            "end": 6074,
            "quote": "Blood pressure is measured in millimeters of mercury"
          },
          {
            "start": 6678,
            "end": 6736,
            "quote": "two or more high blood pressure readings on different days"
          },
          {
            "start": 6813,
            "end": 6844,
            "quote": "your medical and family history"
          },
          {
            "start": 6472,
            "end": 6500,
            "quote": "seek medical care right away"
          }
        ]
      }
    ]
  },
  "nlm-fasting-test": {
    "id": "nlm-fasting-test",
    "version": "989a2020ae03-zh-dcacc7c1bb5b",
    "title": "验血前空腹准备",
    "url": "https://medlineplus.gov/lab-tests/fasting-for-a-blood-test/",
    "publisher": "U.S. National Library of Medicine",
    "jurisdiction": "US",
    "source_language": "en-US",
    "language": "zh-CN-editorial",
    "source_sha256": "989a2020ae03ef56dbe1a899937b243871c4662d415b85bf5e7af450a8b7e81b",
    "license": "US-federal-public-domain-specified-NLM-content",
    "license_url": "https://medlineplus.gov/about/using/usingcontent/",
    "attribution": "Source: MedlinePlus, National Library of Medicine.",
    "clinical_review_status": "not_reviewed",
    "editorial_status": "Codex_editorial_not_official_translation",
    "editorial_text": "空腹验血的准备与例外\n要求空腹时，通常不能进食或喝除白水外的饮料，也应避免口香糖、吸烟和运动。一般空腹8–12小时，但时长由检测项目与医护指示决定；并非所有血糖检查都要空腹，不应在未要求时自行空腹。\n英文依据：except plain water\n8 to 12 hours\nNot all blood glucose tests require fasting\n\n药物和误进食的处理\n空腹期间能否用平常药物，应问医护人员；除非医护明确要求，不应自行停药。若误进食或喝了非白水饮料，需告知医护，可能要重新安排检查。咖啡、果汁、汽水等可能影响结果，不能擅自当作允许饮品。\n英文依据：don't stop taking your medicines unless your provider tells you to stop.\nYou may need to reschedule the test\nJuice, coffee, soda\n\n",
    "raw": "What is fasting for a blood test?\n\nIf your health care provider has told you to fast before a blood test, it means you should not eat or drink anything, except plain water, for several hours before your test. While you're fasting for a blood test, you should also not:\n\n- Chew gum\n- Smoke\n- Exercise\n\nYour provider will give you a copy of instructions to follow if they ask you to fast for a test. If you have any questions not covered in those instructions, ask your provider at least a full day before the test so that you'll have time to properly prepare.\n\nHow long do I have to fast before the test?\n\nYou usually need to fast for 8 to 12 hours before a test. Your provider will tell you exactly how long to fast, depending on what test they've ordered. For certain tests, there may also be additional instructions. For example, you may be asked not to drink alcohol for a longer period of time.\n\nIf your blood test requires fasting, you can usually schedule the test early in the morning. That way, most of your fasting time will be while you are sleeping.\n\nWhy do I need to fast before my blood test?\n\nWhen you eat and drink, your bloodstream absorbs sugar, fat, protein, and other nutrients in those foods and beverages. These nutrients can then change the levels of various substances in your blood and therefore affect the accuracy of your test results. Inaccurate results give your provider an inaccurate view of your health and may lead to a wrong diagnosis.\n\nWhat types of blood tests require fasting?\n\nSome examples of common blood tests that usually require fasting are:\n\n- Blood glucose, also called blood sugar, tests. These tests measure the level of blood glucose in a sample of your blood. They are used to help diagnose and monitor diabetes, prediabetes, and gestational diabetes (diabetes that starts during pregnancy). Not all blood glucose tests require fasting, so ask your provider if you need to fast for your test.\n- Cholesterol levels tests (lipid panel). These tests measure the level of fats, called lipids, in your bloodstream, including cholesterol and triglycerides. The test results help show your risk of getting heart disease and can be used to monitor your health after a cardiac event like a heart attack or stroke.\n- Basic metabolic panel (BMP). This is a group of tests that measures several natural chemicals in your blood. The results give your provider information about how well your organs are working, including your heart, kidneys, and liver.\n\nIn some cases, you may also be asked to fast for:\n\n- Liver function tests. This group of tests measures several proteins and other substances related to your liver function. Test results can give your provider information on your liver's health.\n- Renal function panel. This is a group of tests that measure several waste products and substances related to your kidney function. The results are often used to monitor your kidney function if your provider suspects kidney disease or if you have diabetes.\n\nWhether or not your provider asks you to fast for these tests depends on several factors. For example, some liver function tests only require fasting if they're ordered as part of a comprehensive metabolic panel.\n\nOther types of tests not listed here may require fasting. Therefore, you should always ask your provider if you aren't sure whether you should fast before your test.\n\nCan I drink anything besides water during a fast?\n\nNo. Juice, coffee, soda, and other beverages can get in your bloodstream and affect your results. But you can drink plain water. Avoid lemon-flavored or flavored carbonated water, which may contain sugars or artificial sweeteners. Staying well hydrated can actually make the testing process a little easier. This is because water helps to keep more fluid in your veins, which can make it easier to get a sample of your blood.\n\nCan I continue taking medicine during a fast?\n\nAsk your provider whether it's okay to take your usual prescription medicines and/or over-the-counter medicines. For some tests, they may ask you to stop taking your medicines. But don't stop taking your medicines unless your provider tells you to stop.\n\nLet your provider know about any vitamins and supplements that you take, too. That way you'll be sure to avoid taking anything that could affect your test results.\n\nWhat if I make a mistake and have something to eat or drink besides water during my fast?\n\nTell your provider if you eat or drink before your test. You may need to reschedule the test for another time when you can fast to make sure you get accurate results.\n\nWhen can I eat and drink normally again?\n\nYou'll be able to eat as soon as your test is over. It is common to feel light-headed after a blood test that requires fasting. So, you may want to bring a snack that you can eat right away.\n\nIs there anything else I need to know about fasting before a blood test?\n\nYou should not fast if your provider doesn't tell you to do so. Fasting for some blood tests may also affect your results and give your provider an inaccurate understanding of your health. If you aren't sure if you should fast for a coming blood test, ask your provider as soon as possible. Taking the right steps before a blood test helps make sure your results will be accurate.",
    "sections": [
      {
        "id": "2d13d0c0193bad10807f3c8f2c90f08f504b2d7f73c7e7c11fee06aa175b5040",
        "start": 0,
        "end": 181,
        "text": "空腹验血的准备与例外\n要求空腹时，通常不能进食或喝除白水外的饮料，也应避免口香糖、吸烟和运动。一般空腹8–12小时，但时长由检测项目与医护指示决定；并非所有血糖检查都要空腹，不应在未要求时自行空腹。\n英文依据：except plain water\n8 to 12 hours\nNot all blood glucose tests require fasting",
        "section": "空腹验血的准备与例外",
        "source_spans": [
          {
            "start": 153,
            "end": 171,
            "quote": "except plain water"
          },
          {
            "start": 634,
            "end": 647,
            "quote": "8 to 12 hours"
          },
          {
            "start": 1840,
            "end": 1883,
            "quote": "Not all blood glucose tests require fasting"
          }
        ]
      },
      {
        "id": "e182cd4d0fe83c6c84e48449e86333a84c185025add23f448e28142d77809b90",
        "start": 183,
        "end": 418,
        "text": "药物和误进食的处理\n空腹期间能否用平常药物，应问医护人员；除非医护明确要求，不应自行停药。若误进食或喝了非白水饮料，需告知医护，可能要重新安排检查。咖啡、果汁、汽水等可能影响结果，不能擅自当作允许饮品。\n英文依据：don't stop taking your medicines unless your provider tells you to stop.\nYou may need to reschedule the test\nJuice, coffee, soda",
        "section": "药物和误进食的处理",
        "source_spans": [
          {
            "start": 4082,
            "end": 4154,
            "quote": "don't stop taking your medicines unless your provider tells you to stop."
          },
          {
            "start": 4469,
            "end": 4504,
            "quote": "You may need to reschedule the test"
          },
          {
            "start": 3431,
            "end": 3450,
            "quote": "Juice, coffee, soda"
          }
        ]
      }
    ]
  }
}

export function buildVerifiedSource(
  docId: string,
  sectionIndex: number,
  spanIndices?: number[],
): SourceItem {
  const doc = VERIFIED_NLM_FIXTURE[docId]
  if (!doc) throw new Error('Unknown NLM fixture doc: ' + docId)
  const sec = doc.sections[sectionIndex]
  if (!sec) throw new Error('Unknown NLM section: ' + docId + '#' + sectionIndex)
  if (doc.editorial_text.slice(sec.start, sec.end) !== sec.text) {
    throw new Error('Editorial slice mismatch for ' + docId)
  }
  const rawSpans = spanIndices ? spanIndices.map(i => sec.source_spans[i]!) : sec.source_spans
  for (const sp of rawSpans) {
    if (!sp || sp.end - sp.start !== sp.quote.length || doc.raw.slice(sp.start, sp.end) !== sp.quote) {
      throw new Error('Raw quote offset mismatch in ' + docId)
    }
  }
  return {
    id: sec.id,
    document_id: doc.id,
    source: 'milvus_bge',
    title: doc.title,
    section: sec.section,
    url: doc.url,
    verified: false,
    content: sec.text,
    start: sec.start,
    end: sec.end,
    version: doc.version,
    source_sha256: doc.source_sha256,
    publisher: doc.publisher,
    jurisdiction: doc.jurisdiction,
    source_language: doc.source_language,
    language: doc.language,
    clinical_review_status: doc.clinical_review_status,
    editorial_status: doc.editorial_status,
    license: doc.license,
    attribution: doc.attribution,
    score: null,
    rerank_score: null,
    source_spans: rawSpans.map(sp => ({ start: sp.start, end: sp.end, quote: sp.quote })),
  }
}

export function buildVerifiedEvidenceAnchor(
  evidenceId: string,
  docId: string,
  sectionIndex: number,
  spanIndex: number,
): EvidenceAnchor {
  const doc = VERIFIED_NLM_FIXTURE[docId]
  if (!doc) throw new Error('Unknown NLM fixture doc: ' + docId)
  const sec = doc.sections[sectionIndex]
  if (!sec) throw new Error('Unknown section: ' + docId + '#' + sectionIndex)
  const sp = sec.source_spans[spanIndex]
  if (!sp) throw new Error('Unknown span: ' + docId + '#' + sectionIndex + ':' + spanIndex)
  if (sp.end - sp.start !== sp.quote.length || doc.raw.slice(sp.start, sp.end) !== sp.quote) {
    throw new Error('Anchor offset mismatch in ' + docId)
  }
  return {
    id: evidenceId,
    source_id: sec.id,
    document_id: doc.id,
    source_sha256: doc.source_sha256,
    start: sp.start,
    end: sp.end,
    quote: sp.quote,
    url: doc.url,
  }
}

export const POLICY_NOTICE =
  '资料来自美国NLM/MedlinePlus，中文为编辑解释，未经过医学专业复核；不替代个体诊断或用药建议。'

export const OMITTED_NOTICE_LINE =
  '部分内容缺少充分的原文或项目规则支持，已省略；如需更完整解释，请补充相关原文或向医护核对。'

export interface SimClaimSpec {
  kind: 'medical_fact' | 'project_behavior' | 'corpus_scope' | 'editorial'
  support_status: 'supported' | 'partially_supported' | 'unsupported' | 'contradicted'
  text: string
  note: string
  evidence: EvidenceAnchor[]
  policy_rules?: string[]
  review_round?: number
  review_claim_index?: number
  original_draft_spans?: Array<{ index: number; start: number; end: number; text: string }>
  paragraphBreakAfter?: boolean
}

export function codePointLength(text: string): number {
  return Array.from(text).length
}

export function sliceByCodePoints(text: string, startCp: number, endCp: number): string {
  return Array.from(text).slice(startCp, endCp).join('')
}

export function composeReviewedAnswerAndClaims(specs: SimClaimSpec[]): {
  answer: string
  claim_reviews: ClaimReviewItem[]
  omitted_claim_count: number
} {
  const claim_reviews: ClaimReviewItem[] = []
  let draftPosCp = 0
  let answer = ''
  let answerCpLen = 0
  let omitted = 0

  for (let i = 0; i < specs.length; i++) {
    const s = specs[i]!
    const textCpLen = codePointLength(s.text)
    const draft_start = draftPosCp
    const draft_end = draftPosCp + textCpLen
    draftPosCp = draft_end

    let final_start: number | null = null
    let final_end: number | null = null

    if (s.support_status === 'supported') {
      final_start = answerCpLen
      answer += s.text
      answerCpLen += textCpLen
      final_end = answerCpLen
      if (s.paragraphBreakAfter) {
        answer += '\n\n'
        answerCpLen += 2
      }
    } else {
      omitted++
    }

    claim_reviews.push({
      index: i,
      kind: s.kind,
      support_status: s.support_status,
      evidence_ids: s.evidence.map(e => e.id),
      evidence: s.evidence,
      policy_rules: s.policy_rules ?? [],
      note: s.note,
      text: s.text,
      draft_start,
      draft_end,
      final_start,
      final_end,
      professional_review: 'pending',
      review_round: s.review_round ?? 1,
      review_claim_index: s.review_claim_index ?? i,
      ...(s.original_draft_spans ? { original_draft_spans: s.original_draft_spans } : {}),
    })
  }

  if (answer.endsWith('\n\n')) {
    answer = answer.slice(0, -2)
    answerCpLen -= 2
  }
  if (omitted > 0) {
    answer += '\n' + OMITTED_NOTICE_LINE
    answerCpLen += 1 + codePointLength(OMITTED_NOTICE_LINE)
  }
  const noticeStart = answerCpLen + 1
  answer += '\n' + POLICY_NOTICE
  answerCpLen += 1 + codePointLength(POLICY_NOTICE)

  claim_reviews.push({
    index: claim_reviews.length,
    kind: 'corpus_scope',
    origin: 'program_policy',
    support_status: 'supported',
    evidence_ids: [],
    evidence: [],
    policy_rules: ['educational_scope'],
    note: '程序固定资料范围提示，不计入模型医学支持率。',
    text: POLICY_NOTICE,
    draft_start: null,
    draft_end: null,
    final_start: noticeStart,
    final_end: answerCpLen,
    professional_review: 'pending',
  })

  return {
    answer,
    claim_reviews,
    omitted_claim_count: omitted,
  }
}

export function validateSimulatedRunConsistency(run: RunOut): void {
  if (!run.run_id.startsWith('sim-')) {
    throw new Error(`Simulation run_id must start with sim-: ${run.run_id}`)
  }
  if (!run.request_id.startsWith('sim-')) {
    throw new Error(`Simulation request_id must start with sim-: ${run.request_id}`)
  }
  if (run.checkpoint_id && !run.checkpoint_id.startsWith('sim-')) {
    throw new Error(`Simulation checkpoint_id must start with sim-: ${run.checkpoint_id}`)
  }
  if (!run.session_id.startsWith('sim-')) {
    throw new Error(`Simulation session_id must start with sim-: ${run.session_id}`)
  }
  if (run.clinical_review_status !== 'not_run') {
    throw new Error(`clinical_review_status must be not_run: ${run.clinical_review_status}`)
  }

  for (const src of run.sources || []) {
    const doc = src.document_id ? VERIFIED_NLM_FIXTURE[src.document_id] : undefined
    if (!doc) throw new Error(`Source document_id not in verified fixture: ${src.document_id}`)
    if (src.source_sha256 !== doc.source_sha256) {
      throw new Error(`Source sha256 mismatch for ${src.document_id}`)
    }
    if (src.version !== doc.version) {
      throw new Error(`Source version mismatch for ${src.document_id}`)
    }
    if (
      typeof src.start !== 'number' ||
      typeof src.end !== 'number' ||
      doc.editorial_text.slice(src.start, src.end) !== src.content
    ) {
      throw new Error(`Source editorial slice mismatch for ${src.document_id}`)
    }
    for (const sp of src.source_spans || []) {
      if (
        sp.end - sp.start !== sp.quote.length ||
        doc.raw.slice(sp.start, sp.end) !== sp.quote
      ) {
        throw new Error(
          `Source span mismatch in ${src.document_id}: [${sp.start}..${sp.end}] vs quote length ${sp.quote.length}`,
        )
      }
    }
  }

  for (const claim of run.claim_reviews || []) {
    if (claim.professional_review && claim.professional_review !== 'pending') {
      throw new Error(`Claim professional_review must be pending`)
    }
    if (claim.support_status === 'supported') {
      if (
        claim.final_start === null ||
        claim.final_end === null ||
        !run.answer ||
        (sliceByCodePoints(run.answer, claim.final_start, claim.final_end) !== claim.text &&
          run.answer.slice(claim.final_start, claim.final_end) !== claim.text)
      ) {
        throw new Error(`Supported claim #${claim.index} final_start/final_end does not match answer slice`)
      }
    } else {
      if (claim.final_start !== null || claim.final_end !== null) {
        throw new Error(`Omitted claim #${claim.index} must have null final_start/final_end`)
      }
    }
    for (const ev of claim.evidence || []) {
      const doc = VERIFIED_NLM_FIXTURE[ev.document_id]
      if (!doc) throw new Error(`Claim evidence unknown doc: ${ev.document_id}`)
      if (ev.source_sha256 !== doc.source_sha256) {
        throw new Error(`Claim evidence sha256 mismatch for ${ev.document_id}`)
      }
      if (ev.end - ev.start !== ev.quote.length || doc.raw.slice(ev.start, ev.end) !== ev.quote) {
        throw new Error(`Claim evidence quote offset mismatch for ${ev.document_id}`)
      }
    }
  }

  for (const trace of run.review_trace || []) {
    for (const ev of trace.evidence || []) {
      const doc = VERIFIED_NLM_FIXTURE[ev.document_id]
      if (!doc) throw new Error(`Trace evidence unknown doc: ${ev.document_id}`)
      if (ev.source_sha256 !== doc.source_sha256) {
        throw new Error(`Trace evidence sha256 mismatch for ${ev.document_id}`)
      }
      if (ev.end - ev.start !== ev.quote.length || doc.raw.slice(ev.start, ev.end) !== ev.quote) {
        throw new Error(`Trace evidence quote offset mismatch for ${ev.document_id}`)
      }
    }
  }
}

