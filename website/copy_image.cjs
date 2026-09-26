const fs = require('fs');
const path = require('path');

const src = "C:\\Users\\Ankit\\.gemini\\antigravity-ide\\brain\\a2ef56d4-2aaf-4211-b079-a17e11825b40\\.user_uploaded\\media_1789201669295.jpg";
const dest = "c:\\Users\\Ankit\\Desktop\\Projects\\HORIZON\\website\\public\\images\\architecture_diagram.jpg";

fs.copyFileSync(src, dest);
console.log('Copied successfully to', dest);
