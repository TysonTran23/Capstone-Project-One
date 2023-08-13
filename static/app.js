const BASE_URL = "https:api.sportsdata.io/golf/v2/json";
const URL_KEY = "key=176964ab9ddb48dea44c9fb38e4adbc8";
const currentDate = new Date();
const CURRENTYEAR = currentDate.getFullYear();

const blogContainer = document.getElementById("blog-container");

/////////////////////////////////////////////////////////////////////////////////////////
//Generate HTML/Structure for the News API
function generateNewsHTML(data) {
  return `
    <h4 class="text-center display-6">${data.Title}</h4>
    <p class="text-center">    <a href="${data.OriginalSourceUrl}">Source: ${data.OriginalSource}</a></p>

    <p>${data.Content}</p>
    `;
}

//GET request to API, specifically News
//Use generateNewsHTML() to create HTML for News and add to page
async function getNews() {
  const response = await axios.get(`${BASE_URL}/News?${URL_KEY}`);
  data = response.data;
  for (let item of data) {
    let news = $(generateNewsHTML(item));
    $("#todays-news-container").append(news);
  }
}
/////////////////////////////////////////////////////////////////////////////////////////

//Generate HTML/Structure for the Current Tournament Leaderboard API
function generateLeaderboardHTML(data) {
  return `
    <tr>
        <td>${data.Rank + 1}</td>
        <td>${data.Name}</td>
        <td>${data.TotalScore}</td>
        <td>${data.Rounds[0] ? data.Rounds[0].Score : "-"}</td>
        <td>${data.Rounds[1] ? data.Rounds[1].Score : "-"}</td>
        <td>${data.Rounds[2] ? data.Rounds[2].Score : "-"}</td>
        <td>${data.Rounds[3] ? data.Rounds[3].Score : "-"}</td>
    </tr>
    `;
}

// Get the next tournament ID based on the current date and day of the week
function getNextTournamentId(currentTournamentId) {
  const currentDate = new Date();
  const dayOfWeek = currentDate.getDay();

  //If today is Thursday or later, increment the tournament ID
  if (dayOfWeek === 4) {
    return currentTournamentId + 1;
  } else {
    return currentTournamentId;
  }
}

//GET request to API, specifically CURRENT Tournament Leaderboard
//Use generateLeaderboardHTML() to create HTML for Leaderboard and add to page
async function getLeaderboard() {
  const currentTournamentId = 560;

  const nextTournamentId = getNextTournamentId(currentTournamentId);

  const response = await axios.get(
    `${BASE_URL}/Leaderboard/${nextTournamentId}?${URL_KEY}`
  );
  const players = response.data.Players;
  const tournament = response.data.Tournament.Name;

  const tournamentName = $("#current-tournament-container").find("h4");
  const currentTournament = $("#current-leaderboard-container").find("h2");
  tournamentName.text(tournament);
  currentTournament.text(tournament);

  for (let i = 0; i < 5; i++) {
    let player = $(generateLeaderboardHTML(players[i]));
    $("#leaderboard-body").append(player);
  }
  for (let item of players) {
    let player = $(generateLeaderboardHTML(item));
    $("#current-leaderboard-body").append(player);
  }
}

/////////////////////////////////////////////////////////////////////////////////////////
function genereateNextTournamentHTML(data) {
  return `
  <li>Location: ${data.Location}</li>
  <li>Venue: ${data.Venue}</li>
  <li>Par: ${data.Par}</li>
  <li>Yards: ${data.Yards}</li>
  <li>Start Date: ${data.StartDate}</li>
  <li>End Date: ${data.EndDate}</li>
  `;
}

async function getNextTournament() {
  const currentTournamentId = 561;

  const nextTournamentId = getNextTournamentId(currentTournamentId);

  const response = await axios.get(
    `${BASE_URL}/Leaderboard/${nextTournamentId}?${URL_KEY}`
  );

  const tournament = response.data.Tournament;

  const tournamentName = $("#next-tournament-container").find("h4");
  tournamentName.text(tournament.Name);

  let information = $(genereateNextTournamentHTML(tournament));
  $("#next-tournament-list").append(information);
}
/////////////////////////////////////////////////////////////////////////////////////////
getNews();
getLeaderboard();
getNextTournament();

/////////////////////////////////////////////////////////////////////////////////////////

