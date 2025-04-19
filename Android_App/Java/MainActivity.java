package com.example.detectionapp;

import android.app.ProgressDialog;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.example.detectionapp.databinding.ActivityMainBinding;
import com.google.android.gms.tasks.OnFailureListener;
import com.google.android.gms.tasks.OnSuccessListener;
import com.google.firebase.storage.FirebaseStorage;
import com.google.firebase.storage.StorageReference;
import com.squareup.picasso.Picasso;

public class MainActivity extends AppCompatActivity {

    ActivityMainBinding binding;
    StorageReference storageReference;
    ProgressDialog progressDialog;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        binding.ambilgambar.setOnClickListener(v -> {
            progressDialog = new ProgressDialog(MainActivity.this);
            progressDialog.setMessage("Mengambil Gambar...");
            progressDialog.setCancelable(false);
            progressDialog.show();

            String imageID = binding.namagambar.getText().toString();

            // Initialize FirebaseStorage with the custom bucket URL
            FirebaseStorage storage = FirebaseStorage.getInstance("gs://detection-app-f3849");

            // Correctly build the reference to "Gambar/<imageID>.png" inside your bucket
            storageReference = storage.getReference("Gambar/" + imageID + ".jpg");

            // Get download URL and load with Picasso
            storageReference.getDownloadUrl()
                    .addOnSuccessListener(uri -> {
                        Picasso.get().load(uri).into(binding.gambarhasildeteksi);
                        if (progressDialog.isShowing()) {
                            progressDialog.dismiss();
                        }
                    })
                    .addOnFailureListener(e -> {
                        if (progressDialog.isShowing()) {
                            progressDialog.dismiss();
                        }
                        Toast.makeText(MainActivity.this, "Failed to retrieve", Toast.LENGTH_SHORT).show();
                        e.printStackTrace();  // For debugging purposes
                    });
        });
    }
}
