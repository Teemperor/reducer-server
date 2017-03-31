<!DOCTYPE html>
<html>
<body>

<?php
$target_dir = "/var/reducing/uploads/";
$target_file = $target_dir . basename($_FILES["fileToUpload"]["name"]);
$uploadOk = 1;
$imageFileType = pathinfo($target_file,PATHINFO_EXTENSION);
// Check if file already exists
if (file_exists($target_file)) {
    echo "Sorry, file already exists. This shouldn't happen unless the script forgot to pull the file from the uploads dir...";
    $uploadOk = 0;
}
// Check file size
//if ($_FILES["fileToUpload"]["size"] > 600000000) {
//    echo "Sorry, your file is too large (600MB limit).";
//    $uploadOk = 0;
//}
if($imageFileType != "zip") {
    echo "Sorry, only ZIP files are allowed.";
    $uploadOk = 0;
}

// Check if $uploadOk is set to 0 by an error
if ($uploadOk == 0) {
    echo "Sorry, your file was not uploaded due to an PHP error (or something like that).";
// if everything is ok, try to upload file
} else {
    if (move_uploaded_file($_FILES["fileToUpload"]["tmp_name"], $target_file)) {
        echo "The file ". basename( $_FILES["fileToUpload"]["name"]). " has been uploaded.";
    } else {
        echo "Sorry, there was an error uploading your file.";
    }
}

?>

<a href="status.html"> Back to overview </a>

</body>
</html>
