<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Sonic Slots</title>

  <!-- REQUIRED for Telegram Mini Apps -->
  <script src="https://telegram.org/js/telegram-web-app.js"></script>

  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      height: 100%;
      background: #0a1428;
      color: #fff;
      font-family: 'Segoe UI', system-ui, sans-serif;
      overflow-x: hidden;
    }
    body {
      background: linear-gradient(160deg, #0a1428 0%, #0d1f3c 50%, #071020 100%);
      display: flex;
      justify-content: center;
      padding: 12px;
      min-height: 100%;
    }
    #game {
      width: 100%;
      max-width: 420px;
      background: linear-gradient(180deg, #12243f 0%, #0c1a30 100%);
      border-radius: 20px;
      border: 3px solid #00b4ff;
      box-shadow: 0 0 30px rgba(0,180,255,0.25);
      padding: 16px 14px 20px;
    }
    h1 {
      text-align: center;
      font-size: 26px;
      color: #00e5ff;
      text-shadow: 0 0 12px #00b4ff;
      margin-bottom: 6px;
    }
    .balance-row {
      display: flex;
      justify-content: space-between;
      background: rgba(0,0,0,0.35);
      border-radius: 12px;
      padding: 10px 14px;
      margin-bottom: 10px;
      border: 1px solid #1a3a5c;
    }
    .balance-box { text-align: center; }
    .balance-label { font-size: 11px; color: #8ab4d9; text-transform: uppercase; }
    .balance-value { font-size: 20px; font-weight: 700; color: #ffd700; }
    #message {
      text-align: center;
      min-height: 22px;
      font-size: 14px;
      color: #ffdd55;
      margin-bottom: 10px;
      font-weight: 600;
    }
    .reels-container {
      background: #050d18;
      border-radius: 14px;
      padding: 12px 8px;
      border: 2px solid #1e4a7a;
      margin-bottom: 12px;
    }
    .reels-row { display: flex; justify-content: space-between; gap: 6px; }
    .reel {
      flex: 1;
      background: linear-gradient(180deg, #0a1a30, #071220);
      border-radius: 10px;
      border: 2px solid #2a5a8a;
      height: 130px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .symbol { font-size: 42px; }
    .controls { display: flex; flex-direction: column; gap: 8px; }
    .hold-row, .nudge-row { display: flex; gap: 6px; }
    .hold-row button, .nudge-row button {
      flex: 1; padding: 9px 0; font-size: 12px; font-weight: 700;
      border: none; border-radius: 8px; background: #1a4a7a; color: #cce6ff; cursor: pointer;
    }
    .hold-row button.held {
      background: #ff3333; color: white;
    }
    .hold-row button:disabled, .nudge-row button:disabled { opacity: 0.4; }
    .spin-row { display: flex; gap: 8px; margin-top: 4px; }
    #spinBtn {
      flex: 2; background: linear-gradient(180deg, #00e676, #00a844);
      color: #003310; font-size: 20px; font-weight: 800; padding: 14px 0;
      border: none; border-radius: 12px; cursor: pointer;
    }
    #autoBtn {
      flex: 1; background: #2a3a5a; color: #aaccff;
      font-size: 14px; font-weight: 700; border: none; border-radius: 12px; cursor: pointer;
    }
    .bet-row {
      display: flex; justify-content: center; align-items: center; gap: 12px; margin: 10px 0 6px;
    }
    .bet-row button {
      width: 36px; height: 36px; border-radius: 50%; border: none;
      background: #1a4a7a; color: white; font-size: 20px; font-weight: bold; cursor: pointer;
    }
    #betDisplay { font-size: 16px; font-weight: 700; color: #ffdd55; min-width: 80px; text-align: center; }
    .paytable {
      margin-top: 14px; background: rgba(0,0,0,0.3); border-radius: 10px;
      padding: 10px 12px; font-size: 11px; color: #9ec5e8; line-height: 1.45;
    }
    .paytable strong { color: #00e5ff; }
  </style>
</head>
<body>
<div id="game">
  <h1>🦔 Sonic Slots</h1>

  <div class="balance-row">
    <div class="balance-box">
      <div class="balance-label">Rings</div>
      <div class="balance-value" id="credits">1000</div>
    </div>
    <div class="balance-box">
      <div class="balance-label">Win</div>
      <div class="balance-value" id="winAmount">0</div>
    </div>
  </div>

  <div id="message">Hold is random • Nudge every spin</div>

  <div class="reels-container" id="reelsBox">
    <div class="reels-row">
      <div class="reel"><div class="symbol" id="r0">💍</div></div>
      <div class="reel"><div class="symbol" id="r1">💍</div></div>
      <div class="reel"><div class="symbol" id="r2">💍</div></div>
      <div class="reel"><div class="symbol" id="r3">💍</div></div>
      <div class="reel"><div class="symbol" id="r4">💍</div></div>
    </div>
  </div>

  <div class="controls">
    <div class="hold-row">
      <button id="h0" disabled>Hold</button>
      <button id="h1" disabled>Hold</button>
      <button id="h2" disabled>Hold</button>
      <button id="h3" disabled>Hold</button>
      <button id="h4" disabled>Hold</button>
    </div>
    <div class="nudge-row">
      <button id="n0">Nudge</button>
      <button id="n1">Nudge</button>
      <button id="n2">Nudge</button>
      <button id="n3">Nudge</button>
      <button id="n4">Nudge</button>
    </div>

    <div class="bet-row">
      <button id="betMinus">−</button>
      <div id="betDisplay">Bet: 10</div>
      <button id="betPlus">+</button>
    </div>

    <div class="spin-row">
      <button id="spinBtn">SPIN</button>
      <button id="autoBtn">AUTO</button>
    </div>
  </div>

  <div class="paytable">
    <strong>Paytable</strong><br>
    🦔 Sonic = 500 &nbsp;|&nbsp; 💎 Emerald = 300<br>
    🦊 Tails / 🥊 Knuckles / 🌸 Amy = 150<br>
    💍 Ring = 80 &nbsp;|&nbsp; 🌭 Chili Dog = 40<br>
    🤖 Eggman = Lose rings<br>
    <strong>⭐ on middle reel = BONUS ROUND</strong> (5 Free Spins ×2)
  </div>
</div>

<script>
  // Telegram WebApp ready
  if (window.Telegram && Telegram.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // ========== your original game code below ==========
  const symbols = ['🦔','🦊','🥊','🌸','💍','💎','🤖','🌭','⭐'];
  const values = {
    '🦔': 500, '💎': 300, '🦊': 150, '🥊': 150,
    '🌸': 150, '💍': 80, '🌭': 40, '🤖': -80, '⭐': 0
  };

  let reels = [4,4,4,4,4];
  let held = [false,false,false,false,false];
  let holdAvailable = false;
  let nudgesLeft = 1;
  let credits = 1000;
  let bet = 10;
  let isSpinning = false;
  let autoMode = false;
  let inBonus = false;
  let freeSpinsLeft = 0;
  let bonusMultiplier = 1;

  const reelEls = [0,1,2,3,4].map(i => document.getElementById('r'+i));
  const holdBtns = [0,1,2,3,4].map(i => document.getElementById('h'+i));
  const nudgeBtns = [0,1,2,3,4].map(i => document.getElementById('n'+i));
  const creditsEl = document.getElementById('credits');
  const winEl = document.getElementById('winAmount');
  const msgEl = document.getElementById('message');
  const betEl = document.getElementById('betDisplay');
  const spinBtn = document.getElementById('spinBtn');
  const autoBtn = document.getElementById('autoBtn');
  const reelsBox = document.getElementById('reelsBox');

  // ... rest of your original JS stays the same ...
  // (I left the game logic untouched)

  holdBtns.forEach((btn, i) => {
    btn.addEventListener('click', () => {
      if (!holdAvailable || isSpinning || inBonus) return;
      held[i] = !held[i];
      btn.classList.toggle('held', held[i]);
      btn.textContent = held[i] ? 'HELD' : 'Hold';
    });
  });

  nudgeBtns.forEach((btn, i) => {
    btn.addEventListener('click', () => {
      if (nudgesLeft <= 0 || isSpinning) return;
      reels[i] = (reels[i] + 1) % symbols.length;
      reelEls[i].textContent = symbols[reels[i]];
      nudgesLeft--;
      updateNudgeState();
      msgEl.textContent = nudgesLeft > 0 ? `Nudge left: ${nudgesLeft}` : 'Checking...';
      if (nudgesLeft === 0) checkWin();
    });
  });

  document.getElementById('betMinus').onclick = () => {
    if (bet > 5 && !inBonus) { bet -= 5; updateBet(); }
  };
  document.getElementById('betPlus').onclick = () => {
    if (bet < 50 && !inBonus) { bet += 5; updateBet(); }
  };
  function updateBet() { betEl.textContent = 'Bet: ' + bet; }

  spinBtn.addEventListener('click', () => {
    autoMode = false;
    autoBtn.textContent = 'AUTO';
    spin();
  });
  autoBtn.addEventListener('click', () => {
    autoMode = !autoMode;
    autoBtn.textContent = autoMode ? 'STOP' : 'AUTO';
    if (autoMode) spin();
  });

  function spin() {
    if (isSpinning) return;

    if (!inBonus) {
      if (credits < bet) {
        msgEl.textContent = 'Not enough Rings!';
        autoMode = false;
        autoBtn.textContent = 'AUTO';
        return;
      }
      credits -= bet;
      creditsEl.textContent = credits;
    }

    winEl.textContent = '0';
    isSpinning = true;
    msgEl.textContent = inBonus ? `FREE SPIN ${6 - freeSpinsLeft}/5` : 'Spinning...';

    const spinInterval = setInterval(() => {
      reels.forEach((_, i) => {
        if (!held[i]) {
          const idx = Math.floor(Math.random() * symbols.length);
          reels[i] = idx;
          reelEls[i].textContent = symbols[idx];
        }
      });
    }, 70);

    setTimeout(() => {
      clearInterval(spinInterval);

      reels.forEach((_, i) => {
        if (!held[i]) {
          const idx = Math.floor(Math.random() * symbols.length);
          reels[i] = idx;
          reelEls[i].textContent = symbols[idx];
        }
      });

      isSpinning = false;
      held = [false,false,false,false,false];
      holdBtns.forEach((btn) => {
        btn.classList.remove('held');
        btn.textContent = 'Hold';
      });

      if (!inBonus && symbols[reels[2]] === '⭐') {
        startBonus();
        return;
      }

      nudgesLeft = inBonus ? 0 : 1;
      updateNudgeState();

      if (!inBonus) {
        checkWin();
        if (Math.random() < 0.30) {
          holdAvailable = true;
          updateHoldState();
          msgEl.textContent += ' | 🎯 HOLD FEATURE available!';
        } else {
          holdAvailable = false;
          updateHoldState();
        }
      } else {
        checkWin();
        freeSpinsLeft--;
        if (freeSpinsLeft <= 0) {
          endBonus();
        } else {
          setTimeout(spin, 1400);
        }
        return;
      }

      if (autoMode) setTimeout(spin, 1600);
    }, 1400);
  }

  function startBonus() {
    inBonus = true;
    freeSpinsLeft = 5;
    bonusMultiplier = 2;
    holdAvailable = false;
    nudgesLeft = 0;
    updateHoldState();
    updateNudgeState();
    reelsBox.classList.add('bonus-active');
    msgEl.textContent = '🌟 SPECIAL STAGE! 5 Free Spins ×2';
    setTimeout(spin, 1800);
  }

  function endBonus() {
    inBonus = false;
    bonusMultiplier = 1;
    reelsBox.classList.remove('bonus-active');
    msgEl.textContent = 'Bonus finished!';
    autoMode = false;
    autoBtn.textContent = 'AUTO';
  }

  function checkWin() {
    const counts = {};
    reels.forEach(i => {
      const s = symbols[i];
      counts[s] = (counts[s] || 0) + 1;
    });

    let win = 0;
    let msg = 'No win';
    let penaltyTriggered = false;

    for (const [sym, cnt] of Object.entries(counts)) {
      if (cnt >= 3 && sym !== '⭐') {
        const base = values[sym];
        if (base < 0) {
          const loss = Math.min(Math.abs(base), credits);
          credits -= loss;
          msg = `🤖 Eggman! Lost ${loss}`;
          penaltyTriggered = true;
        } else {
          const multiplier = (cnt === 5 ? 3 : cnt === 4 ? 2 : 1) * bonusMultiplier;
          win = base * multiplier * (bet / 10);
          msg = `${cnt}× \( {sym} → + \){win}` + (bonusMultiplier > 1 ? ' (×2)' : '');
        }
        break;
      }
    }

    if (!penaltyTriggered && win === 0 && Object.values(counts).some(c => c >= 2)) {
      win = 15 * bonusMultiplier * (bet / 10);
      msg = 'Two matching → +' + win + (bonusMultiplier > 1 ? ' (×2)' : '');
    }

    if (win > 0) {
      credits += win;
      winEl.textContent = win;
    }

    creditsEl.textContent = credits;
    msgEl.textContent = msg;
    updateNudgeState();
  }

  function updateHoldState() {
    holdBtns.forEach(btn => btn.disabled = !holdAvailable || isSpinning || inBonus);
  }
  function updateNudgeState() {
    nudgeBtns.forEach(btn => btn.disabled = nudgesLeft <= 0 || isSpinning || inBonus);
  }

  updateHoldState();
  updateNudgeState();
  updateBet();
</script>
</body>
</html>
