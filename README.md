# Rogers Pass Winter Restricted Area Status SMS
**For a live demo, please visit https://rogers-pass.herokuapp.com/**

Rogers Pass Winter Restricted Area Status SMS is a basic site which records a user's phone number and texts them the next morning with the updated Winter Restricted Areas in Roger's Pass BC. When going skiing in the pass, it can be frustrating trying to open the app while on the highway in and out of service twying to figure out where you can ski that morning. This app streamlines the process into a convenient SMS alert.

It's written using Flask in python3, and deployed to Heroku using Postgres as the database. Twilio handles the SMS messaging and Selenium is used to pull the daily updated data. The front end is HTML with some Jinja for dyanmic loading and the CSS is mainly from Pure-CSS.

## Usage

To use this site, enter your phone number in the form on the landing page. As long as you have a verified North American phone number, you will be added to the list and texted in the morning just past 8AM when the area statuses update. If you want to use the service for multiple days you have to re-sign up each day after you have received a SMS notifcation for the current day.

## Limitations

Currently this is only set up for North American numbers. Due to the nature of being deployed to Heroku with a free account there is no garuntee a dyno will be running to execute the send SMS command if the site receives too many monthly requests.

## Contributing

All required files minus the environment variables are included in this GitHub repo. Feel free to take this template and edit it however you would like. I would love to hear about any improvements you make!

## License
[MIT](https://choosealicense.com/licenses/mit/) Free Usage