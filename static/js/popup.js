function customAlert(id) {
    if (id === "delete") {
        if (confirm("파일을 삭제하시겠습니까? \n 파일이 휴지통으로 이동되며, 복원할 수 있습니다.")) {
            // 확인 버튼 클릭 시 동작
            alert("파일이 삭제되었습니다.");
        }
    } else if (id === "auto_delete") {
        if (confirm("자동 삭제하시겠습니까? \n 30일 내에 사용되지 않은 파일이 휴지통으로 이동되며, 복원할 수 있습니다.")) {
            // 확인 버튼 클릭 시 동작
            alert("파일이 자동 삭제되었습니다.");
        }
    } else if (id === "url") {
        if (confirm("파일 링크를 복사하시겠습니까?")) {
            // 확인 버튼 클릭 시 동작
            alert("파일 링크가 복사되었습니다.");
        }
    } else if (id === "download") {
        if (confirm("파일을 다운로드하시겠습니까?")) {
            // 확인 버튼 클릭 시 동작
            alert("파일이 다운로드 되었습니다!");
        }
    } else if (id === "restore") {
        if (confirm("파일을 복원하시겠습니까?")) {
            // 확인 버튼 클릭 시 동작
            alert("파일이 복원 되었습니다!");
        }
    } else if (id === "clear") {
        if (confirm("휴지통의 모든 항목을 완전히 삭제하시겠습니까? \n 복원할 수 없게 됩니다.")) {
            // 확인 버튼 클릭 시 동작
            alert("휴지통을 비웠습니다!");
        }
    } else if (id === "hard_delete") {
        if (confirm("파일을 영구 삭제하시겠습니까? \n 복원할 수 없게 됩니다.")) {
            // 확인 버튼 클릭 시 동작
            alert("파일이 영구 삭제 되었습니다!");
        }
    }
}



function myFunction() {
    /* Get the text field */
    let textarea = document.getElementById("myUrl");
    textarea.select();
    document.execCommand("copy");
    alert("Copied!")

}