const BASE_URL = "https:api.sportsdata.io/golf/v2/json";
const URL_KEY = "key=176964ab9ddb48dea44c9fb38e4adbc8";

const blogContainer = document.getElementById("blog-container");

function generateNewsHTML(data) {
  return `
    <h4>${data.Title}</h4>
    <p>Source: ${data.OriginalSource}</p>
    <a href="${data.OriginalSourceUrl}">${data.OriginalSourceUrl}</a>
    <p>${data.Content}</p>
    `;
}

async function getNews() {
  const response = await axios.get(`${BASE_URL}/News?${URL_KEY}`);
  data = response.data;
  for (let item of data) {
    let news = $(generateNewsHTML(item));
    $("#todays-news-container").append(news);
  }
}

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
    <tr>
    `;
}

async function getLeaderboard() {
  const response = await axios.get(`${BASE_URL}/Leaderboard/560?${URL_KEY}`);
  const players = response.data.Players;
  const tournament = response.data.Tournament.Name;
  console.log(tournament);

  const tournamentName = $("#current-tournament-container").find("h4");
  tournamentName.text(tournament);
  for (let i = 0; i < 5; i++) {
    let player = $(generateLeaderboardHTML(players[i]));
    $("#leaderboard-body").append(player);
  }
}

getNews();
getLeaderboard();
