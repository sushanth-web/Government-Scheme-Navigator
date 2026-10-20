import type { AppLanguage, ProfileField } from "../types";

interface ConversationCopy {
  welcome: string;
  questions: Record<ProfileField, string>;
  thinking: string;
  matches: string;
  checklist: string;
  voiceUnsupported: string;
  speechUnavailable: string;
  fields: Record<ProfileField, string>;
  continue: string;
  chooseScheme: string;
  checklistButton: string;
}

const english: ConversationCopy = {
  welcome: "Hello! I'm SchemeSage. I'll ask a few simple questions to help you explore government schemes. What is your age?",
  questions: {
    age: "Thanks. How do you describe your gender? You can skip this if you prefer.",
    gender: "What kind of work do you do?",
    occupation: "Which district do you live in?",
    district: "About how much is your annual household income? An estimate is fine.",
    income: "Thanks for sharing. Here are a few example scheme matches to explore. These are illustrative, not confirmed eligibility results.",
  },
  thinking: "Looking at the details you shared…",
  matches: "I found a few possibilities to review. Choose the schemes you'd like to include in your checklist.",
  checklist: "Here is your sample checklist. Please confirm requirements and eligibility with the official scheme source before applying.",
  voiceUnsupported: "Voice input isn't supported in this browser. You can still type your answer.",
  speechUnavailable: "Spoken replies aren't available in this browser. You can read the response on screen.",
  fields: { age: "Age", gender: "Gender", occupation: "Occupation", district: "District", income: "Annual income" },
  continue: "Continue",
  chooseScheme: "Choose schemes",
  checklistButton: "Build my checklist",
};

const copyByLanguage: Record<string, ConversationCopy> = {
  English: english,
  Hindi: {
    welcome: "नमस्ते! मैं SchemeSage हूँ। सरकारी योजनाएँ खोजने में मदद के लिए मैं आपसे कुछ आसान सवाल पूछूँगा। आपकी उम्र क्या है?",
    questions: {
      age: "धन्यवाद। आप अपना लिंग कैसे बताना चाहेंगे? चाहें तो इसे छोड़ सकते हैं।",
      gender: "आप क्या काम करते हैं?",
      occupation: "आप किस ज़िले में रहते हैं?",
      district: "आपके परिवार की सालाना आय लगभग कितनी है? अनुमान भी ठीक है।",
      income: "जानकारी साझा करने के लिए धन्यवाद। यहाँ कुछ उदाहरण योजनाएँ हैं। ये केवल शुरुआती सुझाव हैं, पात्रता की पुष्टि नहीं।",
    },
    thinking: "आपकी जानकारी देख रहा हूँ…",
    matches: "इन विकल्पों को देखें। अपनी चेकलिस्ट में शामिल करने वाली योजनाएँ चुनें।",
    checklist: "यह आपकी नमूना चेकलिस्ट है। आवेदन से पहले आधिकारिक स्रोत से पात्रता और ज़रूरी दस्तावेज़ों की पुष्टि करें।",
    voiceUnsupported: "इस ब्राउज़र में आवाज़ से जवाब देना उपलब्ध नहीं है। आप लिखकर जवाब दे सकते हैं।",
    speechUnavailable: "इस ब्राउज़र में आवाज़ में जवाब उपलब्ध नहीं है। आप जवाब स्क्रीन पर पढ़ सकते हैं।",
    fields: { age: "उम्र", gender: "लिंग", occupation: "काम", district: "ज़िला", income: "सालाना आय" },
    continue: "आगे बढ़ें",
    chooseScheme: "योजनाएँ चुनें",
    checklistButton: "मेरी चेकलिस्ट बनाएँ",
  },
  Bengali: {
    welcome: "নমস্কার! আমি SchemeSage। সরকারি প্রকল্প খুঁজতে সাহায্য করার জন্য কয়েকটি সহজ প্রশ্ন করব। আপনার বয়স কত?",
    questions: {
      age: "ধন্যবাদ। আপনার লিঙ্গ কীভাবে জানাতে চান? চাইলে এড়িয়ে যেতে পারেন।",
      gender: "আপনি কী কাজ করেন?",
      occupation: "আপনি কোন জেলায় থাকেন?",
      district: "আপনার পরিবারের বার্ষিক আয় প্রায় কত? আনুমানিক বললেও হবে।",
      income: "তথ্য দেওয়ার জন্য ধন্যবাদ। এগুলি কিছু উদাহরণ প্রকল্প, নিশ্চিত যোগ্যতার ফল নয়।",
    },
    thinking: "আপনার দেওয়া তথ্য দেখছি…",
    matches: "এই সম্ভাব্য প্রকল্পগুলি দেখুন এবং চেকলিস্টে রাখতে চান এমনগুলি বেছে নিন।",
    checklist: "এটি একটি নমুনা চেকলিস্ট। আবেদন করার আগে সরকারি উৎস থেকে যোগ্যতা ও নথি যাচাই করুন।",
    voiceUnsupported: "এই ব্রাউজারে ভয়েস ইনপুট নেই। আপনি লিখে উত্তর দিতে পারেন।",
    speechUnavailable: "এই ব্রাউজারে কথ্য উত্তর পাওয়া যাচ্ছে না। স্ক্রিনে উত্তরটি পড়ুন।",
    fields: { age: "বয়স", gender: "লিঙ্গ", occupation: "পেশা", district: "জেলা", income: "বার্ষিক আয়" },
    continue: "এগিয়ে যান",
    chooseScheme: "প্রকল্প বেছে নিন",
    checklistButton: "আমার চেকলিস্ট তৈরি করুন",
  },
  Gujarati: {
    welcome: "નમસ્તે! હું SchemeSage છું. સરકારી યોજનાઓ શોધવામાં મદદ માટે હું તમને થોડા સરળ પ્રશ્નો પૂછીશ. તમારી ઉંમર કેટલી છે?",
    questions: {
      age: "આભાર. તમે તમારું લિંગ જણાવવા માંગો છો? ઇચ્છો તો આ પ્રશ્ન છોડી શકો છો.",
      gender: "તમે શું કામ કરો છો?",
      occupation: "તમે કયા જિલ્લામાં રહો છો?",
      district: "તમારા પરિવારની વાર્ષિક આવક અંદાજે કેટલી છે? અંદાજ પણ ચાલશે.",
      income: "માહિતી આપવા બદલ આભાર. આ કેટલીક ઉદાહરણ યોજનાઓ છે, પાત્રતાની પુષ્ટિ નથી.",
    },
    thinking: "તમે આપેલી વિગતો જોઈ રહ્યો છું…",
    matches: "આ સંભવિત યોજનાઓ જુઓ અને તમારી ચેકલિસ્ટમાં સામેલ કરવા પસંદ કરો.",
    checklist: "આ નમૂનાની ચેકલિસ્ટ છે. અરજી કરતા પહેલાં સત્તાવાર સ્ત્રોતથી પાત્રતા અને દસ્તાવેજોની ખાતરી કરો.",
    voiceUnsupported: "આ બ્રાઉઝરમાં અવાજથી જવાબ આપવાનું ઉપલબ્ધ નથી. તમે લખીને જવાબ આપી શકો છો.",
    speechUnavailable: "આ બ્રાઉઝરમાં બોલેલો જવાબ ઉપલબ્ધ નથી. તમે સ્ક્રીન પર વાંચી શકો છો.",
    fields: { age: "ઉંમર", gender: "લિંગ", occupation: "વ્યવસાય", district: "જિલ્લો", income: "વાર્ષિક આવક" },
    continue: "આગળ વધો",
    chooseScheme: "યોજનાઓ પસંદ કરો",
    checklistButton: "મારી ચેકલિસ્ટ બનાવો",
  },
  Telugu: {
    welcome: "నమస్కారం! నేను SchemeSage. ప్రభుత్వ పథకాలను కనుగొనడంలో సహాయపడటానికి కొన్ని సులభమైన ప్రశ్నలు అడుగుతాను. మీ వయస్సు ఎంత?",
    questions: {
      age: "ధన్యవాదాలు. మీ లింగాన్ని చెప్పాలనుకుంటున్నారా? కావాలంటే ఈ ప్రశ్నను దాటవేయవచ్చు.",
      gender: "మీరు ఏ పని చేస్తారు?",
      occupation: "మీరు ఏ జిల్లాలో నివసిస్తున్నారు?",
      district: "మీ కుటుంబ వార్షిక ఆదాయం సుమారుగా ఎంత? అంచనా సరిపోతుంది.",
      income: "వివరాలు పంచుకున్నందుకు ధన్యవాదాలు. ఇవి పరిశీలించడానికి కొన్ని ఉదాహరణ పథకాలు మాత్రమే.",
    },
    thinking: "మీరు పంచుకున్న వివరాలను పరిశీలిస్తున్నాను…",
    matches: "ఈ సాధ్యమైన పథకాలను చూడండి. మీ చెక్‌లిస్ట్‌లో చేర్చాలనుకున్న వాటిని ఎంచుకోండి.",
    checklist: "ఇది నమూనా చెక్‌లిస్ట్. దరఖాస్తు చేసే ముందు అధికారిక మూలం ద్వారా అర్హత, పత్రాలను నిర్ధారించండి.",
    voiceUnsupported: "ఈ బ్రౌజర్‌లో వాయిస్ ఇన్‌పుట్‌కు మద్దతు లేదు. మీరు టైప్ చేసి సమాధానం ఇవ్వవచ్చు.",
    speechUnavailable: "ఈ బ్రౌజర్‌లో వాయిస్ సమాధానం అందుబాటులో లేదు. స్క్రీన్‌పై చదవండి.",
    fields: { age: "వయస్సు", gender: "లింగం", occupation: "వృత్తి", district: "జిల్లా", income: "వార్షిక ఆదాయం" },
    continue: "కొనసాగించండి",
    chooseScheme: "పథకాలను ఎంచుకోండి",
    checklistButton: "నా చెక్‌లిస్ట్ రూపొందించండి",
  },
  Marathi: {
    welcome: "नमस्कार! मी SchemeSage आहे. सरकारी योजना शोधण्यात मदत करण्यासाठी मी तुम्हाला काही सोपे प्रश्न विचारेन. तुमचे वय किती आहे?",
    questions: {
      age: "धन्यवाद. तुम्हाला तुमचे लिंग सांगायचे आहे का? तुम्ही हा प्रश्न वगळू शकता.",
      gender: "तुम्ही कोणते काम करता?",
      occupation: "तुम्ही कोणत्या जिल्ह्यात राहता?",
      district: "तुमच्या कुटुंबाचे वार्षिक उत्पन्न अंदाजे किती आहे?",
      income: "माहिती दिल्याबद्दल धन्यवाद. या काही नमुना योजना आहेत, पात्रतेची खात्री नव्हे.",
    },
    thinking: "तुम्ही दिलेली माहिती पाहत आहे…",
    matches: "या संभाव्य योजना पाहा आणि चेकलिस्टमध्ये समाविष्ट करायच्या योजना निवडा.",
    checklist: "ही नमुना चेकलिस्ट आहे. अर्ज करण्यापूर्वी अधिकृत स्रोताकडून पात्रता आणि कागदपत्रे तपासा.",
    voiceUnsupported: "या ब्राउझरमध्ये आवाजातून उत्तर देणे उपलब्ध नाही. तुम्ही टाइप करू शकता.",
    speechUnavailable: "या ब्राउझरमध्ये बोलके उत्तर उपलब्ध नाही. तुम्ही स्क्रीनवर वाचू शकता.",
    fields: { age: "वय", gender: "लिंग", occupation: "व्यवसाय", district: "जिल्हा", income: "वार्षिक उत्पन्न" },
    continue: "पुढे चला",
    chooseScheme: "योजना निवडा",
    checklistButton: "माझी चेकलिस्ट तयार करा",
  },
  Tamil: {
    welcome: "வணக்கம்! நான் SchemeSage. அரசு திட்டங்களைக் கண்டறிய உதவ சில எளிய கேள்விகளைக் கேட்கிறேன். உங்கள் வயது என்ன?",
    questions: {
      age: "நன்றி. உங்கள் பாலினத்தைப் பகிர விரும்புகிறீர்களா? விரும்பினால் தவிர்க்கலாம்.",
      gender: "நீங்கள் என்ன வேலை செய்கிறீர்கள்?",
      occupation: "நீங்கள் எந்த மாவட்டத்தில் வசிக்கிறீர்கள்?",
      district: "உங்கள் குடும்பத்தின் ஆண்டு வருமானம் தோராயமாக எவ்வளவு?",
      income: "விவரங்களைப் பகிர்ந்ததற்கு நன்றி. இவை எடுத்துக்காட்டு திட்டங்கள் மட்டுமே; தகுதி உறுதி செய்யப்படவில்லை.",
    },
    thinking: "நீங்கள் பகிர்ந்த விவரங்களைப் பார்க்கிறேன்…",
    matches: "இந்த சாத்தியமான திட்டங்களைப் பார்த்து, பட்டியலில் சேர்க்க விரும்புவதைத் தேர்ந்தெடுக்கவும்.",
    checklist: "இது மாதிரி பட்டியல். விண்ணப்பிப்பதற்கு முன் அதிகாரப்பூர்வ ஆதாரத்தில் தகுதி மற்றும் ஆவணங்களை உறுதிப்படுத்தவும்.",
    voiceUnsupported: "இந்த உலாவியில் குரல் உள்ளீடு இல்லை. நீங்கள் தட்டச்சு செய்து பதிலளிக்கலாம்.",
    speechUnavailable: "இந்த உலாவியில் குரல் பதில் கிடைக்காது. திரையில் படிக்கலாம்.",
    fields: { age: "வயது", gender: "பாலினம்", occupation: "தொழில்", district: "மாவட்டம்", income: "ஆண்டு வருமானம்" },
    continue: "தொடரவும்",
    chooseScheme: "திட்டங்களைத் தேர்ந்தெடுக்கவும்",
    checklistButton: "எனது பட்டியலை உருவாக்கு",
  },
  Kannada: {
    welcome: "ನಮಸ್ಕಾರ! ನಾನು SchemeSage. ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲು ಸಹಾಯ ಮಾಡಲು ಕೆಲವು ಸರಳ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳುತ್ತೇನೆ. ನಿಮ್ಮ ವಯಸ್ಸು ಎಷ್ಟು?",
    questions: {
      age: "ಧನ್ಯವಾದಗಳು. ನಿಮ್ಮ ಲಿಂಗವನ್ನು ಹಂಚಿಕೊಳ್ಳಲು ಬಯಸುವಿರಾ? ಬೇಕಿದ್ದರೆ ಇದನ್ನು ಬಿಟ್ಟುಬಿಡಬಹುದು.",
      gender: "ನೀವು ಯಾವ ಕೆಲಸ ಮಾಡುತ್ತೀರಿ?",
      occupation: "ನೀವು ಯಾವ ಜಿಲ್ಲೆಯಲ್ಲಿ ವಾಸಿಸುತ್ತೀರಿ?",
      district: "ನಿಮ್ಮ ಕುಟುಂಬದ ವಾರ್ಷಿಕ ಆದಾಯ ಅಂದಾಜು ಎಷ್ಟು?",
      income: "ವಿವರ ಹಂಚಿಕೊಂಡಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು. ಇವು ಮಾದರಿ ಯೋಜನೆಗಳು ಮಾತ್ರ; ಅರ್ಹತೆ ದೃಢೀಕರಣವಲ್ಲ.",
    },
    thinking: "ನೀವು ಹಂಚಿಕೊಂಡ ವಿವರಗಳನ್ನು ನೋಡುತ್ತಿದ್ದೇನೆ…",
    matches: "ಈ ಸಾಧ್ಯ ಯೋಜನೆಗಳನ್ನು ನೋಡಿ, ನಿಮ್ಮ ಪರಿಶೀಲನಾ ಪಟ್ಟಿಗೆ ಸೇರಿಸಲು ಬಯಸುವವುಗಳನ್ನು ಆರಿಸಿ.",
    checklist: "ಇದು ಮಾದರಿ ಪಟ್ಟಿ. ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ಮೊದಲು ಅಧಿಕೃತ ಮೂಲದಿಂದ ಅರ್ಹತೆ ಮತ್ತು ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
    voiceUnsupported: "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಇನ್‌ಪುಟ್ ಲಭ್ಯವಿಲ್ಲ. ನೀವು ಟೈಪ್ ಮಾಡಿ ಉತ್ತರಿಸಬಹುದು.",
    speechUnavailable: "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಉತ್ತರ ಲಭ್ಯವಿಲ್ಲ. ಪರದೆಯಲ್ಲಿ ಓದಬಹುದು.",
    fields: { age: "ವಯಸ್ಸು", gender: "ಲಿಂಗ", occupation: "ಉದ್ಯೋಗ", district: "ಜಿಲ್ಲೆ", income: "ವಾರ್ಷಿಕ ಆದಾಯ" },
    continue: "ಮುಂದುವರಿಸಿ",
    chooseScheme: "ಯೋಜನೆಗಳನ್ನು ಆಯ್ಕೆಮಾಡಿ",
    checklistButton: "ನನ್ನ ಪಟ್ಟಿಯನ್ನು ರಚಿಸಿ",
  },
  Malayalam: {
    welcome: "നമസ്കാരം! ഞാൻ SchemeSage ആണ്. സർക്കാർ പദ്ധതികൾ കണ്ടെത്താൻ സഹായിക്കുന്നതിന് കുറച്ച് ലളിതമായ ചോദ്യങ്ങൾ ചോദിക്കാം. നിങ്ങളുടെ പ്രായം എത്രയാണ്?",
    questions: {
      age: "നന്ദി. നിങ്ങളുടെ ലിംഗം പങ്കുവയ്ക്കാമോ? വേണമെങ്കിൽ ഈ ചോദ്യം ഒഴിവാക്കാം.",
      gender: "നിങ്ങൾ എന്ത് ജോലി ചെയ്യുന്നു?",
      occupation: "നിങ്ങൾ ഏത് ജില്ലയിലാണ് താമസിക്കുന്നത്?",
      district: "നിങ്ങളുടെ കുടുംബത്തിന്റെ വാർഷിക വരുമാനം ഏകദേശം എത്രയാണ്?",
      income: "വിവരങ്ങൾ പങ്കുവച്ചതിന് നന്ദി. ഇവ ഉദാഹരണ പദ്ധതികളാണ്; യോഗ്യത ഉറപ്പാക്കിയതല്ല.",
    },
    thinking: "നിങ്ങൾ പങ്കുവച്ച വിവരങ്ങൾ പരിശോധിക്കുന്നു…",
    matches: "ഈ സാധ്യതയുള്ള പദ്ധതികൾ പരിശോധിച്ച് പട്ടികയിൽ ഉൾപ്പെടുത്തേണ്ടവ തിരഞ്ഞെടുക്കുക.",
    checklist: "ഇത് ഒരു മാതൃകാ പട്ടികയാണ്. അപേക്ഷിക്കുന്നതിന് മുമ്പ് ഔദ്യോഗിക ഉറവിടത്തിൽ യോഗ്യതയും രേഖകളും ഉറപ്പാക്കുക.",
    voiceUnsupported: "ഈ ബ്രൗസറിൽ ശബ്ദ ഇൻപുട്ട് ലഭ്യമല്ല. നിങ്ങൾക്ക് ടൈപ്പ് ചെയ്ത് മറുപടി നൽകാം.",
    speechUnavailable: "ഈ ബ്രൗസറിൽ ശബ്ദ മറുപടി ലഭ്യമല്ല. സ്ക്രീനിൽ വായിക്കാം.",
    fields: { age: "പ്രായം", gender: "ലിംഗം", occupation: "തൊഴിൽ", district: "ജില്ല", income: "വാർഷിക വരുമാനം" },
    continue: "തുടരുക",
    chooseScheme: "പദ്ധതികൾ തിരഞ്ഞെടുക്കുക",
    checklistButton: "എന്റെ പട്ടിക തയ്യാറാക്കുക",
  },
  Punjabi: {
    welcome: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ SchemeSage ਹਾਂ। ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਲੱਭਣ ਵਿੱਚ ਮਦਦ ਲਈ ਮੈਂ ਕੁਝ ਸੌਖੇ ਸਵਾਲ ਪੁੱਛਾਂਗਾ। ਤੁਹਾਡੀ ਉਮਰ ਕਿੰਨੀ ਹੈ?",
    questions: {
      age: "ਧੰਨਵਾਦ। ਕੀ ਤੁਸੀਂ ਆਪਣਾ ਲਿੰਗ ਦੱਸਣਾ ਚਾਹੋਗੇ? ਤੁਸੀਂ ਇਹ ਸਵਾਲ ਛੱਡ ਸਕਦੇ ਹੋ।",
      gender: "ਤੁਸੀਂ ਕਿਹੜਾ ਕੰਮ ਕਰਦੇ ਹੋ?",
      occupation: "ਤੁਸੀਂ ਕਿਹੜੇ ਜ਼ਿਲ੍ਹੇ ਵਿੱਚ ਰਹਿੰਦੇ ਹੋ?",
      district: "ਤੁਹਾਡੇ ਪਰਿਵਾਰ ਦੀ ਸਾਲਾਨਾ ਆਮਦਨ ਲਗਭਗ ਕਿੰਨੀ ਹੈ?",
      income: "ਜਾਣਕਾਰੀ ਸਾਂਝੀ ਕਰਨ ਲਈ ਧੰਨਵਾਦ। ਇਹ ਕੁਝ ਮਿਸਾਲੀ ਯੋਜਨਾਵਾਂ ਹਨ, ਪਾਤਰਤਾ ਦੀ ਪੁਸ਼ਟੀ ਨਹੀਂ।",
    },
    thinking: "ਤੁਹਾਡੇ ਸਾਂਝੇ ਕੀਤੇ ਵੇਰਵੇ ਵੇਖ ਰਿਹਾ ਹਾਂ…",
    matches: "ਇਨ੍ਹਾਂ ਸੰਭਾਵੀ ਯੋਜਨਾਵਾਂ ਨੂੰ ਵੇਖੋ ਅਤੇ ਆਪਣੀ ਸੂਚੀ ਵਿੱਚ ਸ਼ਾਮਲ ਕਰਨ ਲਈ ਚੁਣੋ।",
    checklist: "ਇਹ ਇੱਕ ਨਮੂਨਾ ਸੂਚੀ ਹੈ। ਅਰਜ਼ੀ ਦੇਣ ਤੋਂ ਪਹਿਲਾਂ ਸਰਕਾਰੀ ਸਰੋਤ ਤੋਂ ਪਾਤਰਤਾ ਅਤੇ ਦਸਤਾਵੇਜ਼ਾਂ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ।",
    voiceUnsupported: "ਇਸ ਬ੍ਰਾਊਜ਼ਰ ਵਿੱਚ ਆਵਾਜ਼ੀ ਇਨਪੁੱਟ ਉਪਲਬਧ ਨਹੀਂ ਹੈ। ਤੁਸੀਂ ਲਿਖ ਕੇ ਜਵਾਬ ਦੇ ਸਕਦੇ ਹੋ।",
    speechUnavailable: "ਇਸ ਬ੍ਰਾਊਜ਼ਰ ਵਿੱਚ ਬੋਲਿਆ ਜਵਾਬ ਉਪਲਬਧ ਨਹੀਂ ਹੈ। ਤੁਸੀਂ ਸਕ੍ਰੀਨ ਉੱਤੇ ਪੜ੍ਹ ਸਕਦੇ ਹੋ।",
    fields: { age: "ਉਮਰ", gender: "ਲਿੰਗ", occupation: "ਕਿੱਤਾ", district: "ਜ਼ਿਲ੍ਹਾ", income: "ਸਾਲਾਨਾ ਆਮਦਨ" },
    continue: "ਜਾਰੀ ਰੱਖੋ",
    chooseScheme: "ਯੋਜਨਾਵਾਂ ਚੁਣੋ",
    checklistButton: "ਮੇਰੀ ਸੂਚੀ ਬਣਾਓ",
  },
};

export const getConversationCopy = (language: AppLanguage): ConversationCopy =>
  copyByLanguage[language.name] ?? english;

export const profileFields: ProfileField[] = [
  "age",
  "gender",
  "occupation",
  "district",
  "income",
];

export const demoSchemes = [
  {
    id: "farmer-support",
    name: "Farmer household support",
    note: "Example scheme match · review official criteria",
    icon: "✳",
    tone: "sage",
  },
  {
    id: "student-support",
    name: "Education assistance",
    note: "Example scheme match · review official criteria",
    icon: "▤",
    tone: "lilac",
  },
  {
    id: "family-welfare",
    name: "Family welfare support",
    note: "Example scheme match · review official criteria",
    icon: "⌂",
    tone: "peach",
  },
];

export const demoDocuments = [
  "Income certificate",
  "Proof of residence",
  "Occupation or scheme-specific certificate",
];
