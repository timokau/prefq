// Get videos
var left_preferred = document.getElementById('left_preferred');
var right_preferred = document.getElementById('right_preferred');
// Get buttons
var left_video = document.getElementById('left_video');
var right_video = document.getElementById('right_video');
// Use to iterate over videos
var iterator = 2;

const videos = [
  "/static/lunarlander_random/01.mp4",
  "/static/lunarlander_random/02.mp4",
  "/static/lunarlander_random/03.mp4",
  "/static/lunarlander_random/04.mp4",
  "/static/lunarlander_random/05.mp4",
  "/static/lunarlander_random/06.mp4",
  "/static/lunarlander_random/07.mp4",
  "/static/lunarlander_random/08.mp4",
  "/static/lunarlander_random/09.mp4",
  "/static/lunarlander_random/10.mp4",
];


function changevid() {
  left_video.setAttribute("src", videos[iterator]);
  right_video.setAttribute("src", videos[iterator+1]);
  iterator = (iterator+2) % 10;
}


// signal handler for buttons

left_preferred.addEventListener('click', function() {
  changevid();
});

right_preferred.addEventListener('click', function() {
  changevid();
});