// Get videos
var on_left_preferred = document.getElementById('left_preferred')
var on_right_preferred = document.getElementById('right_preferred')
// Get buttons
var left_video = document.getElementById('left_video')
var right_video = document.getElementById('right_video')
// Use to iterate over videos
var iterator = 0;

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

let is_left_preferred  = new Array(5).fill(null)


function changevid() {
  iterator = (iterator+2) % 10;
  left_video.setAttribute("src", videos[iterator])
  right_video.setAttribute("src", videos[iterator+1])
  if(iterator == 0){
    sendData()
  }
}

function sendData() {
  
  // Create JavaScript API to create AJAX requests (HTTP request made by browser-resident Javascript)
  const xhr = new XMLHttpRequest()
  
  const data = {
    is_left_preferred: is_left_preferred,
  };

  // Set the HTTP method and endpoint URL
  xhr.open('POST', '/')

  // Set the http request header (indicates json datatype to receiving server)
  xhr.setRequestHeader('Content-Type', 'application/json')

  // Convert and send data object to JSON string
  const jsonData = JSON.stringify(data)
  xhr.send(jsonData)
}

// signal handlers for buttons
on_left_preferred.addEventListener('click', function() {

  is_left_preferred[iterator/2] = true

  changevid()
})

on_right_preferred.addEventListener('click', function() {

  is_left_preferred[iterator/2] = false

  changevid()
})