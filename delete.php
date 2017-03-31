<?php



if (preg_match("/^[a-zA-Z0-9_]+.zip$/", $_GET['file'])) {
    touch("/var/reducing/delete/" . $_GET['file']);
}

header("Location: status.html");
die();
?>
