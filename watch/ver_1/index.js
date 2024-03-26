setInterval(() =>{

    d=new Date(); //object of date()
    hr = d.getHours();
    min = d.getMinutes();
    sec = d.getSeconds();

    hr_rotation = 30 * hr + min / 2; //converting current time
    min_rotation = 6 * min;
    sec_rotation = 6 * sec;

    hour.style.transform = `rotate(${hr_rotation}deg)`;
    minute.style.transform = `rotate(${min_rotation}deg)`;
    second.style.transform = `rotate(${sec_rotation}deg)`;

    // Display the date in the middle right of the clock
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    const day= d.getDate();
    const month=monthNames[d.getMonth()];
    const year = d.getFullYear();

    // Hate.innerHTML = '${day} ${month} ${year); // Update the content of the 'date' div with the formatted date string

    date.innerHTML = `${day}`; // Update the content of the 'date' div with the formatted date string

}, 1000);




